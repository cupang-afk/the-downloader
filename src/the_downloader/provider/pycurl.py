from pathlib import Path

import pycurl

from ..constants import CA_CERT_PATH
from ..error import CallbackNonZeroReturnError, ProviderError
from ..task import DownloadTask
from ..types import ProgressCallback
from .base import DownloadProvider, SubprocessDownloaderMixin


class PycurlError(ProviderError):
    """Represent an error class for PycURL download provider exceptions."""

    pass


class PycurlDownloader(DownloadProvider, SubprocessDownloaderMixin):
    """Implement a PycURL download provider."""

    def download(
        self,
        task: DownloadTask,
        dest: Path,
        progress_callback: ProgressCallback,
    ) -> None:
        """Download a file using PycURL.

        Args:
            task: The download task containing URL and metadata
            dest: Destination path for the downloaded file
            progress_callback: Callback function for progress updates

        Raises:
            PycurlError: If the download fails
        """
        if task.is_canceled:
            return

        # Prepare
        callback_error: BaseException | None = None

        def callback(_, d: int, *__: object) -> int:
            nonlocal callback_error
            try:
                if task.is_canceled:
                    return 1
                self._handle_progress_callback(progress_callback, task, d, task.total)
                return 0
            except BaseException as e:
                callback_error = e
                return 1

        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, task.url)
        curl.setopt(pycurl.FOLLOWLOCATION, True)
        curl.setopt(pycurl.HTTPHEADER, [f"{k}: {v}" for k, v in task.headers.items()])
        curl.setopt(pycurl.CAINFO, CA_CERT_PATH)
        curl.setopt(pycurl.BUFFERSIZE, self.chunk_size)
        curl.setopt(pycurl.NOPROGRESS, False)
        curl.setopt(pycurl.XFERINFOFUNCTION, callback)

        error: BaseException | None = None

        # Execute
        with dest.open("wb") as f:
            try:
                curl.setopt(pycurl.WRITEDATA, f)
                curl.perform()
            except Exception as e:
                error = e
            finally:
                curl.close()

            self._handle_curl_error(callback_error, CallbackNonZeroReturnError, task)
            self._handle_curl_error(error, PycurlError, task)

    def _handle_curl_error(
        self,
        err: BaseException | None,
        exc_type: type[ProviderError],
        task: DownloadTask,
    ) -> None:
        """Handle errors from PycURL download operations.

        Args:
            err: The exception that occurred, or None
            exc_type: The exception type to raise for non-KeyboardInterrupt errors
            task: The download task for error context

        Raises:
            KeyboardInterrupt: If the error is a keyboard interrupt or abort signal
            ProviderError: For other download errors
        """
        if err is None:
            return

        # Preserve KeyboardInterrupt
        if isinstance(err, KeyboardInterrupt):
            raise err.with_traceback(err.__traceback__)

        # Handle pycurl-specific errors
        if isinstance(err, pycurl.error):
            err_code = err.args[0]

            # E_ABORTED_BY_CALLBACK: Callback interrupted the transfer
            # E_WRITE_ERROR: Failed to write data to the file
            #
            # sometime CTRL+C did not fire E_ABORTED_BY_CALLBACK but E_WRITE_ERROR
            if err_code in (pycurl.E_ABORTED_BY_CALLBACK, pycurl.E_WRITE_ERROR):
                raise KeyboardInterrupt from err.with_traceback(err.__traceback__)

        # Wrap other errors
        raise exc_type(
            f"Error downloading {task.url} for {task.dest.name}"
        ) from err.with_traceback(err.__traceback__)
