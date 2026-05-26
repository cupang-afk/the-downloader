import os
import random
import socket
import subprocess
import time
import xmlrpc.client
from pathlib import Path, PurePath
from typing import cast, override

from ..constants import DEFAULT_CA_CERT_PATH, DEFAULT_CHUNK_SIZE, DEFAULT_TIMEOUT
from ..exceptions import DownloadProviderError
from ..types.protocol import CheckCanceled, UpdateProgress
from ..utils.file import delete, resolve_binary
from ..utils.network import check_open_port
from .base import BaseProvider, ProviderSubprocessMixin


class Aria2Error(DownloadProviderError):
    pass


class Aria2Provider(BaseProvider, ProviderSubprocessMixin):
    def __init__(
        self,
        aria2c_bin_path: str | Path | None = None,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        timeout: int = DEFAULT_TIMEOUT,
        ca_cert_path: str = DEFAULT_CA_CERT_PATH,
    ) -> None:
        super().__init__(
            chunk_size=chunk_size,
            timeout=timeout,
            ca_cert_path=ca_cert_path,
        )
        self.bin: Path = resolve_binary(
            aria2c_bin_path or ("aria2c" if os.name != "nt" else "aria2c.exe")
        )
        self.process: subprocess.Popen[bytes] | None = None
        self.token: str = f"token:{random.randint(100000, 999999)}"
        self.rpc_secret: str = self.token.split(":", 1)[1]
        self.rpc_server: xmlrpc.client.ServerProxy | None = None

    @override
    def __pre_hook__(self) -> None:
        host: str = "localhost"
        port: int = 0
        for port in range(6800, 7000 + 1):
            if not check_open_port(port):
                continue
            break
        if not port:
            raise Aria2Error("No available port found for aria2c")
        rpc_url = f"http://{host}:{port}/rpc"

        cmd = [
            str(self.bin),
            "--ca-certificate",
            self.ca_cert_path,
            "--file-allocation",
            "none",
            "--enable-rpc",
            "--rpc-secret",
            self.token.split(":", 1)[1],
            "--rpc-listen-port",
            str(port),
            "--rpc-allow-origin-all",
            "--max-concurrent-downloads",
            "999",
            "--allow-overwrite",
        ]
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for RPC server to be ready
        max_retries = 10
        for _ in range(max_retries):
            try:
                with socket.create_connection((host, port), timeout=1):
                    break
            except TimeoutError, ConnectionRefusedError:
                time.sleep(0.5)
        else:
            self.__post_hook__()
            raise Aria2Error("Failed to start aria2c RPC server.")

        self.rpc_server = xmlrpc.client.ServerProxy(rpc_url)

    @override
    def __post_hook__(self) -> None:
        if self.process:
            self.popen_terminate(
                self.process,
                raise_nonzero_return=False,
                terminate_timeout=DEFAULT_TIMEOUT,
            )
            self.process = None
        self.rpc_server = None

    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        if not self.rpc_server:
            raise Aria2Error("RPC server is not running.")

        gid = cast(
            str,
            self.rpc_server.aria2.addUri(
                self.token,
                [url],
                {
                    "dir": str(dest.parent),
                    "out": dest.name,
                    "headers": [f"{k}: {v}" for k, v in headers.items()],
                },
            ),
        )
        # status is fetched at least once so cleanup knows whether aria2
        # has accepted the download and can safely remove it from active tasks.
        status_pulled: bool = False
        state: str | None = None
        try:
            while True:
                if check_canceled():
                    self.rpc_server.aria2.remove(self.token, gid)
                    return
                status = cast(
                    dict[str, str],
                    self.rpc_server.aria2.tellStatus(
                        self.token,
                        gid,
                        ["status", "completedLength", "errorMessage", "totalLength"],
                    ),
                )
                state = status.get("status")
                downloaded = int(status.get("completedLength", "0"))
                total = int(status.get("totalLength", "0"))
                update_progress(downloaded, total)

                if state != "active":
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
        if self.rpc_server is None:
            return

        try:
            if status_pulled and state != "active":
                self.rpc_server.aria2.remove(self.token, gid)
            self.rpc_server.aria2.removeDownloadResult(self.token, gid)
        except (ConnectionError, OSError, xmlrpc.client.Error) as e:
            self.get_logger().debug(
                "Ignoring aria2 RPC cleanup failure for gid %s: %s",
                gid,
                e,
            )
