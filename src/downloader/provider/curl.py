"""Curl-based download provider implementation."""

import os
import threading
from pathlib import Path

import certifi
import requests

from ..callback import ProgressCallback
from ..task import DownloadTask
from .base import CANCEL_EVENT, CHUNK_SIZE, DownloadSubprocessProvider


class CurlDownloader(DownloadSubprocessProvider):
    """Download provider using the curl binary.

    This provider downloads files using HTTP/HTTPS with curl,
    supporting streaming downloads and progress callbacks.
    """

    def __init__(
        self,
        cancel_event: threading.Event = CANCEL_EVENT,
        chunk_size: int = CHUNK_SIZE,
        curl_bin: Path | None = None,
    ) -> None:
        self.bin = self.ensure_binary(
            curl_bin or ("curl" if os.name != "nt" else "curl.exe")
        )
        self.cmd = [str(self.bin), "-sLo-"]
        self.opt = ["--cacert", str(Path(certifi.where()).absolute())]
        super().__init__(cancel_event, chunk_size)

    def download(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback,
    ) -> None:
        """Downloads a file using curl.

        Args:
            task: The download task containing URL, destination, and headers.
            progress_callback: Callback function to report download progress.
        """
        if self.is_canceled:
            return

        dest_path = task.dest if isinstance(task.dest, Path) else None
        if dest_path is None:
            raise ValueError("task.dest must be a Path object")

        cmd_headers = [f"-H {x}: {y}" for x, y in task.headers.items()]

        with (
            dest_path.open("wb") as f,
            self.popen_wrapper(self.cmd + self.opt + cmd_headers + [task.url]) as p,
            requests.get(
                task.url,
                headers=task.headers,
                stream=True,
            ) as head,
        ):
            head.raise_for_status()
            downloaded = 0
            total = int(head.headers.get("Content-Length", 0))

            while p.poll() is None and not self.is_canceled:
                if not p.stdout:
                    break
                chunk: bytes = p.stdout.read(self.chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                self._handle_progress(task, progress_callback, downloaded, total)
