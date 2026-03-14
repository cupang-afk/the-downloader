import os
import socket
import subprocess
import time
import xmlrpc.client
from pathlib import Path
from threading import Lock
from typing import Any

from ..constants import CA_CERT_PATH, CHUNK_SIZE
from ..error import ProviderError
from ..task import DownloadTask
from ..types import ProgressCallback
from ..utils.file_utils import safe_delete
from .base import DownloadProvider, SubprocessDownloaderMixin


class Aria2Error(ProviderError):
    """Represent an error class for Aria2 download provider exceptions."""

    pass


class Aria2Downloader(DownloadProvider, SubprocessDownloaderMixin):
    """Implement an Aria2 download provider."""

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        aria2c_bin: str | Path | None = None,
        aria2c_token: str = "token",
        max_download: int = 999,
    ) -> None:
        """Initialize the Aria2 downloader.

        Args:
            chunk_size: Size of chunks to use for downloading data
            aria2c_bin: Path to the aria2c binary executable
            aria2c_token: Authentication token for Aria2 RPC
            max_download: Maximum number of concurrent downloads
        """
        super().__init__(chunk_size)
        self.bin = self.resolve_binary(
            aria2c_bin or ("aria2c" if os.name != "nt" else "aria2c.exe")
        )
        self.max_download = max_download
        self.aria2_process: subprocess.Popen | None = None
        self.aria2: xmlrpc.client.ServerProxy | None = None
        self.aria2_secret = aria2c_token
        self.aria2_token = f"token:{self.aria2_secret}"
        self.aria2_lock = Lock()

    def __pre_start__(self) -> None:
        port: int | None = next(
            (i for i in range(6800, 7001) if self._check_port(i)), None
        )

        if port is None:
            raise RuntimeError("No available port found for Aria2 RPC")

        if self.aria2_process is None:
            cmd = [
                str(self.bin),
                "--ca-certificate",
                CA_CERT_PATH,
                "--file-allocation",
                "none",
                "--enable-rpc",
                "--rpc-secret",
                self.aria2_secret,
                "--rpc-listen-port",
                str(port),
                "--rpc-allow-origin-all",
                "--max-concurrent-downloads",
                str(self.max_download),
            ]
            if os.name == "nt":
                cmd = " ".join(cmd)
            self.aria2_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

        if self.aria2 is None:
            self.aria2 = xmlrpc.client.ServerProxy(f"http://localhost:{port}/rpc")

    def __post_stop__(self) -> None:
        if self.aria2_process is not None:
            self.popen_terminate(self.aria2_process, raise_nonzero_return=False)
            self.aria2_process = None
        if self.aria2 is not None:
            self.aria2 = None

    def download(
        self,
        task: DownloadTask,
        dest: Path,
        progress_callback: ProgressCallback,
    ) -> None:
        """Download a file using Aria2.

        Args:
            task: The download task containing URL and metadata
            dest: Destination path for the downloaded file
            progress_callback: Callback function for progress updates

        Raises:
            Aria2Error: If the download fails
        """
        if task.is_canceled:
            return

        # Prepare
        gid: Any = None
        status_dict: dict[str, Any] = {}

        # Execute
        try:
            gid = self._add_download(task, dest)
            status_dict: dict[str, Any] = {}

            while True:
                if task.is_canceled:
                    break
                with self.aria2_lock:
                    try:
                        status = self._aria_tell_status(
                            gid,
                            "status",
                            "completedLength",
                            "errorMessage",
                            ttl_hash=round(time.time() / 1),  # ttl for 1 second
                        )
                    except (xmlrpc.client.Fault, OSError):
                        continue

                status_dict = status
                if status_dict.get("status") != "active":
                    break

                downloaded = int(status_dict.get("completedLength", 0))
                self._handle_progress_callback(
                    progress_callback,
                    task,
                    downloaded,
                    task.total,
                )
                time.sleep(1)
        except Exception as e:
            raise Aria2Error(
                f"Error downloading {task.url} for {task.dest.name}"
            ) from e
        finally:
            self._cleanup_download(gid, status_dict)
            safe_delete(dest.with_name(dest.name + ".aria2"))
            if status_dict.get("status") == "error":
                raise Aria2Error(
                    status_dict.get(
                        "errorMessage", "There is an error in Aria2 but unknown"
                    )
                )

    def _check_port(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            try:
                sock.bind(("127.0.0.1", port))
                return True
            except OSError:
                return False

    def _get_ttl_hash(self, seconds: int = 60) -> int:
        return round(time.time() / seconds)

    def _aria_tell_status(
        self, gid: str, *key: str, ttl_hash: int | None = None
    ) -> Any:
        del ttl_hash
        assert self.aria2 is not None, "Aria2 RPC not initialized"
        return self.aria2.aria2.tellStatus(self.aria2_token, gid, [*key])

    def _add_download(self, task: DownloadTask, dest_path: Path) -> Any:
        with self.aria2_lock:
            if self.aria2 is None:
                raise RuntimeError("Aria2 RPC not initialized")
            return self.aria2.aria2.addUri(
                self.aria2_token,
                [task.url],
                {
                    "dir": str(dest_path.parent),
                    "out": dest_path.name,
                    "allow-overwrite": "true",
                    "headers": [f"{k}: {v}" for k, v in task.headers.items()],
                },
            )

    def _cleanup_download(self, gid: Any, status_dict: dict[str, Any]) -> None:
        try:
            with self.aria2_lock:
                assert self.aria2 is not None, "Aria2 RPC not initialized"
                if gid is not None:
                    if status_dict.get("status") == "active":
                        self.aria2.aria2.remove(self.aria2_token, gid)
                    self.aria2.aria2.removeDownloadResult(self.aria2_token, gid)
        except (xmlrpc.client.Fault, OSError):
            pass
