"""Requests-based download provider implementation."""

from pathlib import Path

import requests

from ..callback import ProgressCallback
from ..task import DownloadTask
from .base import DownloadProvider


class RequestsDownloader(DownloadProvider):
    """Download provider using the requests library.

    This provider downloads files using HTTP/HTTPS with the requests library,
    supporting streaming downloads and progress callbacks.
    """

    def download(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback,
    ) -> None:
        """Downloads a file using the requests library.

        Args:
            task: The download task containing URL, destination, and headers.
            progress_callback: Callback function to report download progress.
        """
        if self.is_canceled:
            return

        dest_path = task.dest if isinstance(task.dest, Path) else None
        if dest_path is None:
            raise ValueError("task.dest must be a Path object")

        with (
            requests.get(
                task.url,
                headers=task.headers,
                stream=True,
            ) as res,
            dest_path.open("wb") as f,
        ):
            res.raise_for_status()
            total = int(res.headers.get("Content-Length", 0))

            downloaded = 0
            for chunk in res.iter_content(self.chunk_size):
                if self.is_canceled:
                    break
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                self._handle_progress(task, progress_callback, downloaded, total)
