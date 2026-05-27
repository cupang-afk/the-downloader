"""Wget download provider implementation.

This module provides a download provider that uses the wget command-line tool.
"""

import os
from pathlib import Path, PurePath
from typing import IO, cast, override

from ..exceptions import DownloadProviderError
from ..types.protocol import CheckCanceled, UpdateProgress
from ..utils.file import resolve_binary
from ..utils.metadata import get_total_size
from ..utils.session import get_requests_session
from .base import (
    DEFAULT_CA_CERT_PATH,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_TIMEOUT,
    BaseProvider,
    ProviderSubprocessMixin,
)


class WgetError(DownloadProviderError):
    """Exception raised for errors in the Wget provider."""

    pass


class WgetProvider(BaseProvider, ProviderSubprocessMixin):
    """Download provider that uses wget.

    This provider runs the wget command-line tool as a subprocess to download files.
    """

    def __init__(
        self,
        wget_bin_path: str | Path | None = None,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        timeout: int = DEFAULT_TIMEOUT,
        ca_cert_path: str = DEFAULT_CA_CERT_PATH,
    ) -> None:
        """Initialize the Wget provider.

        Args:
            wget_bin_path: Optional path to the wget binary.
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
            wget_bin_path or ("wget" if os.name != "nt" else "wget.exe")
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
        """Download a file using wget.

        Args:
            url: The URL of the file to download.
            dest: The destination path.
            headers: HTTP headers to include in the request.
            check_canceled: A callback to check if the download should be canceled.
            update_progress: A callback to update the download progress.

        Raises:
            WgetError: If wget fails to download the file.
        """
        if check_canceled():
            return

        cmd = [str(self._bin), "--output-document=-", "--quiet"]
        opt: list[str] = [
            "--timeout",
            str(self.timeout),
            "--ca-certificate",
            self.ca_cert_path,
        ]

        cmd_headers: list[str] = []
        for k, v in headers.items():
            cmd_headers.extend(["--header", f"{k}: {v}"])

        # get total size
        downloaded: int = 0
        total = get_total_size(get_requests_session(), url, headers)

        # execute
        try:
            with (
                open(dest, "wb") as f,
                self.popen_wrapper(
                    cmd + opt + cmd_headers + [url],
                    raise_non_zero_return=False,
                    terminate_timeout=self.timeout,
                ) as p,
            ):
                if not p.stdout:
                    raise WgetError("No output from wget")
                while True:
                    if check_canceled():
                        break
                    chunk = cast(IO[bytes], p.stdout).read(self.chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)

                    downloaded += len(chunk)
                    update_progress(downloaded, total)
        except Exception as e:
            if check_canceled():
                return
            raise WgetError(f"Download failed: {e}") from e
