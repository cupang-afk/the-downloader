"""Requests download provider implementation.

This module provides a download provider that uses the requests library.
"""

from logging import Logger
from pathlib import PurePath
from typing import override

from ..exceptions import DownloadProviderError
from ..types.protocol import CheckCanceled, UpdateProgress
from ..utils.session import get_requests_session
from .base import BaseProvider


class RequestsError(DownloadProviderError):
    """Exception raised for errors in the Requests provider."""

    pass


class RequestsProvider(BaseProvider):
    """Download provider that uses the requests library.

    This provider uses the requests library to download files synchronously.
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
        """Download a file using requests.

        Args:
            url: The URL of the file to download.
            dest: The destination path.
            headers: HTTP headers to include in the request.
            check_canceled: A callback to check if the download should be canceled.
            update_progress: A callback to update the download progress.

        Raises:
            RequestsError: If the request fails or the download is interrupted.
        """
        _logger: Logger = self.get_logger()
        if check_canceled():
            _logger.debug("Canceled before start")
            return

        try:
            session = get_requests_session()
            res = session.get(
                url,
                headers=headers,
                stream=True,
                allow_redirects=True,
                timeout=self.timeout,
                verify=self.ca_cert_path,
            )
            res.raise_for_status()
            downloaded: int = 0
            total: int = int(res.headers.get("Content-Length", -1))
            with open(dest, "wb") as f:
                for chunk in res.iter_content(self.chunk_size):
                    if check_canceled():
                        _logger.debug("Canceled — %d/%d bytes", downloaded, total)
                        return
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    update_progress(downloaded, total)
        except Exception as e:
            if check_canceled():
                return
            raise RequestsError(f"Download failed: {e}") from e
