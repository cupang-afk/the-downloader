"""Aria2-based download provider implementation."""

import os
import socket
import subprocess
import threading
import time
import xmlrpc.client
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import certifi
import requests

from ..callback import ProgressCallback
from ..task import DownloadTask
from .base import CANCEL_EVENT, CHUNK_SIZE, DownloadSubprocessProvider

ARIA2_LOCK = threading.Lock()


class Aria2Error(Exception):
    """Exception raised when Aria2 encounters an error during download."""

    pass


def _is_port_available(port: int) -> bool:
    """Check if a port is available for binding.

    Args:
        port: The port number to check.

    Returns:
        True if the port is available, False otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _get_ttl_hash(seconds: int = 60) -> int:
    """Generate a time-based TTL hash for caching.

    Args:
        seconds: The time window in seconds. Defaults to 60.

    Returns:
        The current TTL hash value.
    """
    return round(time.time() / seconds)


class Aria2Downloader(DownloadSubprocessProvider):
    """Download provider using the aria2c binary.

    This provider downloads files using HTTP/HTTPS with aria2c,
    supporting streaming downloads and progress callbacks.
    """

    def __init__(
        self,
        cancel_event: threading.Event = CANCEL_EVENT,
        chunk_size: int = CHUNK_SIZE,
        aria2c_bin: Path | None = None,
        max_download: int = 999,
        aria2_token: str = "token",
    ) -> None:
        """Initializes the Aria2 download provider.

        Args:
            cancel_event: Threading event used to signal download cancellation.
            chunk_size: Size of chunks for reading/writing data in bytes.
            aria2c_bin: Path to the aria2c binary. Defaults to system binary.
            max_download: Maximum concurrent downloads. Defaults to 999.
            aria2_token: Secret token for RPC authentication. Defaults to "token".
        """
        self.bin = self.ensure_binary(
            aria2c_bin or ("aria2c" if os.name != "nt" else "aria2c.exe")
        )
        self.max_download = max_download
        self._running: subprocess.Popen | None = None
        self.aria2: xmlrpc.client.ServerProxy | None = None
        self.aria2_secret = aria2_token
        self.aria2_token = f"token:{self.aria2_secret}"
        self.aria2_lock = ARIA2_LOCK
        super().__init__(cancel_event, chunk_size)

    def __pre_download__(self) -> None:
        """Prepare aria2c RPC server before downloading."""
        port: int | None = next(
            (i for i in range(6800, 7001) if _is_port_available(i)), None
        )

        if port is None:
            raise RuntimeError("No available port found for Aria2 RPC")

        if self._running is None:
            cmd = [
                str(self.bin),
                "--ca-certificate",
                str(Path(certifi.where()).absolute()),
                "--file-allocation",
                "none",
                "--enable-rpc",
                "--rpc-secret",
                str(self.aria2_secret),
                "--rpc-listen-port",
                str(port),
                "--rpc-allow-origin-all",
                "--max-concurrent-downloads",
                str(self.max_download),
            ]
            if os.name == "nt":
                cmd = " ".join(cmd)
            self._running = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

        if self.aria2 is None:
            self.aria2 = cast(
                xmlrpc.client.ServerProxy,
                xmlrpc.client.ServerProxy(f"http://localhost:{port}/rpc"),
            )

    def __post_download__(self) -> None:
        """Clean up aria2c RPC server after downloading."""
        if self._running is not None:
            self.popen_terminate(self._running, raise_nonzero_return=False)
            self._running = None
        if self.aria2 is not None:
            self.aria2 = None

    @lru_cache()
    def _aria_tell_status(
        self, gid: str, *key: str, ttl_hash: int | None = None
    ) -> Any:
        """Get the status of an aria2 download.

        Args:
            gid: The GID (download ID) of the download.
            *key: Keys to retrieve from the status.
            ttl_hash: Time-based hash for caching. Defaults to None.

        Returns:
            The status information from aria2.
        """
        del ttl_hash
        assert self.aria2 is not None, "Aria2 RPC not initialized"
        return self.aria2.aria2.tellStatus(self.aria2_token, gid, [*key])

    def download(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback,
    ) -> None:
        """Downloads a file using aria2c.

        Args:
            task: The download task containing URL, destination, and headers.
            progress_callback: Callback function to report download progress.
        """
        if self.is_canceled:
            return

        dest_path = task.dest if isinstance(task.dest, Path) else None
        if dest_path is None:
            raise ValueError("task.dest must be a Path object")

        with requests.get(task.url, headers=task.headers, stream=True) as head:
            head.raise_for_status()
            total = int(head.headers.get("Content-Length", 0))

        gid: Any = None
        status: Any = None
        status_dict: dict[str, Any] = {}
        try:
            with self.aria2_lock:
                assert self.aria2 is not None, "Aria2 RPC not initialized"
                gid = self.aria2.aria2.addUri(
                    self.aria2_token,
                    [task.url],
                    {
                        "dir": str(dest_path.parent),
                        "out": dest_path.name,
                        "allow-overwrite": "true",
                        "headers": [f"{k}: {v}" for k, v in task.headers.items()],
                    },
                )
            while not self.is_canceled:
                with self.aria2_lock:
                    try:
                        status = self._aria_tell_status(
                            gid,
                            "status",
                            "completedLength",
                            "errorMessage",
                            ttl_hash=_get_ttl_hash(1),
                        )
                    except xmlrpc.client.Fault:
                        continue
                    except OSError:
                        continue

                status_dict = status
                if status_dict.get("status") != "active":
                    break

                downloaded = int(status_dict.get("completedLength", 0))
                self._handle_progress(task, progress_callback, downloaded, total)

        finally:
            try:
                with self.aria2_lock:
                    assert self.aria2 is not None, "Aria2 RPC not initialized"
                    if gid is not None:
                        if (
                            status_dict is not None
                            and status_dict.get("status") == "active"
                        ):
                            self.aria2.aria2.remove(self.aria2_token, gid)
                        self.aria2.aria2.removeDownloadResult(self.aria2_token, gid)
            except (xmlrpc.client.Fault, OSError):
                pass
            dest_path.with_name(dest_path.name + ".aria2").unlink(missing_ok=True)
            if status is not None and status_dict.get("status") == "error":
                raise Aria2Error(
                    status_dict.get(
                        "errorMessage", "There is an error in Aria2 but unknown"
                    )
                )
