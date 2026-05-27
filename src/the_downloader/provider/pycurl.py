"""Pycurl download provider implementation.

This module provides a download provider that uses the pycurl library, which
is a Python interface to libcurl.
"""

from pathlib import PurePath
from typing import Protocol, override

import pycurl

from ..exceptions import DownloadProviderError
from ..types.protocol import BinaryIOProtocol, CheckCanceled, UpdateProgress
from .base import BaseProvider


class _PycurlProgressCallback(Protocol):
    """Protocol for the pycurl progress callback."""

    def __call__(
        self,
        total: float,
        downloaded: float,
        _upload_total: float,
        _uploaded: float,
    ) -> int | None:
        """Callback for pycurl progress.

        Args:
            total: Total number of bytes to download.
            downloaded: Number of bytes downloaded so far.
            _upload_total: Total number of bytes to upload.
            _uploaded: Number of bytes uploaded so far.

        Returns:
            Non-zero value to abort the download, zero or None to continue.
        """
        ...


class PycurlError(DownloadProviderError):
    """Exception raised for errors in the Pycurl provider."""

    pass


def _create_progress_callback(
    callback_errors: list[BaseException],
    check_canceled: CheckCanceled,
    update_progress: UpdateProgress,
) -> _PycurlProgressCallback:
    """Create a progress callback for pycurl.

    Args:
        callback_errors: A list to store any exceptions raised in the callback.
        check_canceled: A callback to check if the download should be canceled.
        update_progress: A callback to update the download progress.

    Returns:
        A function that follows the `_PycurlProgressCallback` protocol.
    """

    def callback(
        total: float,
        downloaded: float,
        _upload_total: float,
        _uploaded: float,
    ) -> int | None:
        if check_canceled():
            return 1
        try:
            update_progress(int(downloaded), int(total))
        except BaseException as e:
            callback_errors.append(e)
            return 1
        else:
            return 0

    return callback


def _set_options(
    curl: pycurl.Curl,
    url: str,
    file_obj: BinaryIOProtocol,
    headers: dict[str, str],
    ca_cert_path: str,
    timeout: int,
    chunk_size: int,
    progress_callback: _PycurlProgressCallback,
) -> None:
    """Set options for a pycurl Curl instance.

    Args:
        curl: The pycurl Curl instance.
        url: The URL to download.
        file_obj: The file object to write the downloaded data to.
        headers: HTTP headers to include in the request.
        ca_cert_path: Path to the CA certificate bundle.
        timeout: The timeout in seconds for the connection.
        chunk_size: The size of the buffer for the download.
        progress_callback: The progress callback function.
    """
    # cSpell:words setopt FOLLOWLOCATION FAILONERROR HTTPHEADER
    # cSpell:words CAINFO CONNECTTIMEOUT BUFFERSIZE NOSIGNAL NOPROGRESS
    # cSpell:words XFERINFOFUNCTION WRITEDATA
    formatted_headers = [f"{k}: {v}" for k, v in headers.items()]
    for option, value in [
        (pycurl.URL, url),
        (pycurl.FOLLOWLOCATION, True),
        (pycurl.FAILONERROR, True),
        (pycurl.HTTPHEADER, formatted_headers),
        (pycurl.CAINFO, ca_cert_path),
        (pycurl.CONNECTTIMEOUT, timeout),
        (pycurl.BUFFERSIZE, chunk_size),
        (pycurl.NOPROGRESS, False),
        (pycurl.XFERINFOFUNCTION, progress_callback),
        (pycurl.WRITEDATA, file_obj),
    ]:
        curl.setopt(option, value)  # pyright: ignore[reportUnknownMemberType]


def _handle_callback_error(callback_errors: list[BaseException]) -> None:
    """Handle any errors that occurred during a pycurl callback.

    Args:
        callback_errors: A list of exceptions raised during callbacks.

    Raises:
        BaseException: The first exception found in `callback_errors`.
    """
    for e in callback_errors:
        raise e.with_traceback(e.__traceback__)


def _handle_pycurl_error(
    pycurl_error: pycurl.error,
    callback_errors: list[BaseException],
    check_canceled: CheckCanceled,
    url: str,
) -> None:
    """Handle an error from pycurl.

    Args:
        pycurl_error: The pycurl error instance.
        callback_errors: A list of exceptions raised during callbacks.
        check_canceled: A callback to check if the download should be canceled.
        url: The URL that was being downloaded.

    Raises:
        PycurlError: A wrapped error with more information.
    """
    pycurl_error_code = pycurl_error.args[0] if pycurl_error.args else None
    if check_canceled() and pycurl_error_code in (
        pycurl.E_ABORTED_BY_CALLBACK,
        pycurl.E_WRITE_ERROR,
    ):
        return

    _handle_callback_error(callback_errors)

    message = pycurl_error.args[1] if len(pycurl_error.args) > 1 else str(pycurl_error)
    raise PycurlError(
        f"Download failed: {url} [{pycurl_error_code}] {message}"
    ) from pycurl_error


class PycurlProvider(BaseProvider):
    """Download provider that uses the pycurl library.

    This provider uses the pycurl library to download files efficiently.
    """

    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        """Download a file using pycurl.

        Args:
            url: The URL of the file to download.
            dest: The destination path.
            headers: HTTP headers to include in the request.
            check_canceled: A callback to check if the download should be canceled.
            update_progress: A callback to update the download progress.

        Raises:
            PycurlError: If pycurl fails to download the file.
        """
        if check_canceled():
            return

        callback_errors: list[BaseException] = []
        curl = pycurl.Curl()
        try:
            progress_callback = _create_progress_callback(
                callback_errors,
                check_canceled,
                update_progress,
            )
            with open(dest, "wb") as f:
                _set_options(
                    curl,
                    url,
                    f,
                    headers,
                    self.ca_cert_path,
                    self.timeout,
                    self.chunk_size,
                    progress_callback,
                )
                curl.perform()
            _handle_callback_error(callback_errors)
        except pycurl.error as e:
            _handle_pycurl_error(e, callback_errors, check_canceled, url)
        except Exception as e:
            raise PycurlError(f"Download failed: {e}") from e
        finally:
            curl.close()
