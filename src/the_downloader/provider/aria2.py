"""Aria2 download provider implementation.

This module provides a download provider that uses the aria2c command-line tool
via its XML-RPC interface.
"""

import os
import random
import socket
import subprocess
import time
import xmlrpc.client
from logging import Logger
from pathlib import Path, PurePath
from typing import IO, cast, override

from ..exceptions import DownloadProviderError
from ..types.protocol import CheckCanceled, UpdateProgress
from ..utils.file import delete, resolve_binary
from .base import (
    DEFAULT_CA_CERT_PATH,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_TIMEOUT,
    BaseProvider,
    ProviderSubprocessMixin,
)


class Aria2Error(DownloadProviderError):
    """Exception raised for errors in the Aria2 provider."""

    pass


class Aria2Provider(BaseProvider, ProviderSubprocessMixin):
    """Download provider that uses aria2c.

    This provider starts an aria2c RPC server and communicates with it
    to manage downloads.
    """

    def __init__(
        self,
        aria2c_bin_path: str | Path | None = None,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        timeout: int = DEFAULT_TIMEOUT,
        ca_cert_path: str = DEFAULT_CA_CERT_PATH,
    ) -> None:
        """Initialize the Aria2 provider.

        Args:
            aria2c_bin_path: Optional path to the aria2c binary.
            chunk_size: The size of data chunks to read/write.
            timeout: The timeout in seconds for network operations.
            ca_cert_path: Path to the CA certificate bundle.
        """
        super().__init__(
            chunk_size=chunk_size,
            timeout=timeout,
            ca_cert_path=ca_cert_path,
        )
        self._bin: Path = resolve_binary(
            aria2c_bin_path or ("aria2c" if os.name != "nt" else "aria2c.exe")
        )
        self._rpc_process: subprocess.Popen[bytes] | None = None
        self._rpc_token: str = f"token:{random.randint(100000, 999999)}"
        self._rpc_server: xmlrpc.client.ServerProxy | None = None

    @override
    def __pre_hook__(self) -> None:
        """Start the aria2c RPC server before downloading.

        Tries ports 6800-7000 sequentially. starts aria2c directly
        and detects EADDRINUSE from its stderr — zero probing on the happy path.
        """
        host: str = "localhost"

        for port in range(6800, 7001):
            rpc_url = f"http://{host}:{port}/rpc"
            cmd = [
                str(self._bin),
                "--ca-certificate",
                self.ca_cert_path,
                "--file-allocation",
                "none",
                "--enable-rpc",
                "--rpc-secret",
                self._rpc_token.split(":", 1)[1],
                "--rpc-listen-port",
                str(port),
                "--rpc-allow-origin-all",
                "--max-concurrent-downloads",
                "999",
                "--allow-overwrite",
            ]

            self._rpc_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,  # capture to detect EADDRINUSE
                stdin=subprocess.DEVNULL,
            )

            ready = False
            for _ in range(10):
                if self._rpc_process.poll() is not None:
                    break  # process died — check stderr below
                try:
                    with socket.create_connection((host, port), timeout=0.5):
                        ready = True
                        break
                except TimeoutError, ConnectionRefusedError:
                    time.sleep(0.3)

            if ready:
                self._rpc_server = xmlrpc.client.ServerProxy(rpc_url)
                return

            # cSpell: words EADDRINUSE
            if self._rpc_process.poll() is not None:
                stderr = (
                    cast(IO[bytes], self._rpc_process.stderr).read() or b""
                ).decode()
                if "EADDRINUSE" in stderr or "Address already in use" in stderr:
                    self.get_logger().warning("Port %d in use, trying next", port)
                    self._rpc_process = None
                    continue  # try next port

                # Some other failure — abort immediately
                raise Aria2Error(
                    f"aria2c exited on port {port}: {stderr or 'unknown error'}"
                )

            self.popen_terminate(self._rpc_process, False, DEFAULT_TIMEOUT)
            self._rpc_process = None
            raise Aria2Error(
                f"aria2c started on port {port} but RPC endpoint never became reachable"
            )

        raise Aria2Error("No available port found for aria2c (6800-7000 all in use)")

    @override
    def __post_hook__(self) -> None:
        """Stop the aria2c RPC server after downloading."""
        if self._rpc_process:
            self.popen_terminate(
                self._rpc_process,
                raise_nonzero_return=False,
                terminate_timeout=DEFAULT_TIMEOUT,
            )
            self._rpc_process = None
        self._rpc_server = None

    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        """Download a file using aria2c.

        Args:
            url: The URL of the file to download.
            dest: The destination path.
            headers: HTTP headers to include in the request.
            check_canceled: A callback to check if the download should be canceled.
            update_progress: A callback to update the download progress.

        Raises:
            Aria2Error: If the RPC server is not running or the download fails.
        """
        _logger: Logger = self.get_logger()
        if not self._rpc_server:
            _logger.error("RPC server is not running")
            raise Aria2Error("RPC server is not running.")

        gid = cast(
            str,
            self._rpc_server.aria2.addUri(
                self._rpc_token,
                [url],
                {
                    "dir": str(dest.parent),
                    "out": dest.name,
                    "headers": [f"{k}: {v}" for k, v in headers.items()],
                },
            ),
        )
        _logger.debug("GID: %s", gid)
        # status is fetched at least once so cleanup knows whether aria2
        # has accepted the download and can safely remove it from active tasks.
        status_pulled: bool = False
        state: str | None = None
        try:
            while True:
                if check_canceled():
                    _logger.debug("Canceled — GID %s", gid)
                    self._rpc_server.aria2.remove(self._rpc_token, gid)
                    return
                status = cast(
                    dict[str, str],
                    self._rpc_server.aria2.tellStatus(
                        self._rpc_token,
                        gid,
                        [
                            "status",
                            "completedLength",
                            "errorMessage",
                            "totalLength",
                        ],
                    ),
                )
                state = status.get("status")
                downloaded = int(status.get("completedLength", "0"))
                total = int(status.get("totalLength", "0"))
                update_progress(downloaded, total)

                if state != "active":
                    _logger.debug("Download %s state: %s", gid, state)
                    break

                if not status_pulled:
                    status_pulled = True

                # because we requesting status to aria2rpc
                # this need to be throttled
                time.sleep(0.5)
        except Exception as e:
            if check_canceled():
                return
            raise Aria2Error(f"Download failed: {e}") from e
        finally:
            self._cleanup_download_result(gid, status_pulled, state)
            dot_aria2 = dest.with_name(dest.with_suffix(".aria2").name)
            delete(str(dot_aria2))

    def _cleanup_download_result(
        self,
        gid: str,
        status_pulled: bool,
        state: str | None,
    ) -> None:
        """Clean up download results from the aria2c RPC server.

        Args:
            gid: The GID of the download to clean up.
            status_pulled: Whether the status has been pulled at least once.
            state: The final state of the download.
        """
        if self._rpc_server is None:
            return

        try:
            self.get_logger().debug(
                "Cleanup download result for gid %s: %s, %s, %s",
                gid,
                status_pulled,
                state,
                self._rpc_server,
            )
            if status_pulled and state != "active":
                self._rpc_server.aria2.remove(self._rpc_token, gid)
            self._rpc_server.aria2.removeDownloadResult(self._rpc_token, gid)
        except (ConnectionError, OSError, xmlrpc.client.Error) as e:
            self.get_logger().debug(
                "Ignoring aria2 RPC cleanup failure for gid %s: %s", gid, e
            )
