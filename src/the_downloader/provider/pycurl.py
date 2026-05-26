from pathlib import PurePath
from typing import Protocol, override

import pycurl

from ..constants import DEFAULT_CA_CERT_PATH, DEFAULT_CHUNK_SIZE, DEFAULT_TIMEOUT
from ..exceptions import DownloadProviderError
from ..types.protocol import BinaryIOProtocol, CheckCanceled, UpdateProgress
from .base import BaseProvider


class _PycurlProgressCallback(Protocol):
    def __call__(
        self,
        total: float,
        downloaded: float,
        _upload_total: float,
        _uploaded: float,
    ) -> int | None: ...


class PycurlError(DownloadProviderError):
    pass


def _create_progress_callback(
    callback_errors: list[BaseException],
    check_canceled: CheckCanceled,
    update_progress: UpdateProgress,
) -> _PycurlProgressCallback:
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
    for e in callback_errors:
        raise e.with_traceback(e.__traceback__)


def _handle_pycurl_error(
    pycurl_error: pycurl.error,
    callback_errors: list[BaseException],
    check_canceled: CheckCanceled,
    url: str,
) -> None:
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
    def __init__(
        self,
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

    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
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
