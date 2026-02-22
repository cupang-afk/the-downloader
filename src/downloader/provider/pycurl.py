"""Pycurl-based download provider implementation."""

from pathlib import Path

import certifi
import pycurl
import requests

from ..callback import ProgressCallback
from ..task import DownloadTask
from .base import DownloadProvider


class PycurlDownloader(DownloadProvider):
    """Download provider using the pycurl library.

    This provider downloads files using HTTP/HTTPS with pycurl,
    supporting streaming downloads and progress callbacks.
    """

    def download(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback,
    ) -> None:
        """Downloads a file using pycurl.

        Args:
            task: The download task containing URL, destination, and headers.
            progress_callback: Callback function to report download progress.
        """
        if self.is_canceled:
            return

        dest_path = task.dest if isinstance(task.dest, Path) else None
        if dest_path is None:
            raise ValueError("task.dest must be a Path object")

        with requests.get(
            task.url,
            headers=task.headers,
            stream=True,
        ) as head:
            head.raise_for_status()
            total = int(head.headers.get("Content-Length", 0))

        callback_error: BaseException | None = None

        def _callback(_, d, *__):
            nonlocal callback_error

            try:
                if self.is_canceled:
                    return 1
                return self._handle_progress(task, progress_callback, d, total)
            except (BaseException, Exception, KeyboardInterrupt) as e:
                callback_error = e
                return 1

        with dest_path.open("wb") as f:
            curl = pycurl.Curl()
            curl.setopt(pycurl.URL, task.url)
            curl.setopt(pycurl.WRITEDATA, f)
            curl.setopt(pycurl.FOLLOWLOCATION, True)
            curl.setopt(
                pycurl.HTTPHEADER,
                [f"{k}: {v}" for k, v in {**task.headers}.items()],
            )
            curl.setopt(pycurl.CAINFO, str(Path(certifi.where()).absolute()))
            curl.setopt(pycurl.BUFFERSIZE, self.chunk_size)
            curl.setopt(pycurl.NOPROGRESS, False)
            curl.setopt(pycurl.XFERINFOFUNCTION, _callback)

            error = None
            try:
                curl.perform()
            except Exception as e:
                error = e
            finally:
                curl.close()

            if callback_error is not None and not self.is_canceled:
                raise callback_error.with_traceback(callback_error.__traceback__)

            if error is not None and not self.is_canceled:
                raise error.with_traceback(error.__traceback__)
