import os
from os import PathLike
from pathlib import Path

from ..constants import CA_CERT_PATH, CHUNK_SIZE
from ..error import ProviderError
from ..task import DownloadTask
from ..types import ProgressCallback
from .base import DownloadProvider, SubprocessDownloaderMixin


class CurlError(ProviderError):
    """Represent an error class for cURL download provider exceptions."""

    pass


class CurlDownloader(DownloadProvider, SubprocessDownloaderMixin):
    """Implement a cURL download provider."""

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        curl_bin: str | PathLike[str] | None = None,
    ) -> None:
        """Initialize the cURL downloader.

        Args:
            chunk_size: Size of chunks to use for downloading data
            curl_bin: Path to the curl binary executable
        """
        super().__init__(chunk_size)
        self.bin = self.resolve_binary(
            curl_bin or ("curl" if os.name != "nt" else "curl.exe")
        )
        self.cmd = [str(self.bin), "-sLo-"]
        self.opt = ["--cacert", CA_CERT_PATH]

    def download(
        self,
        task: DownloadTask,
        dest: Path,
        progress_callback: ProgressCallback,
    ) -> None:
        """Download a file using cURL.

        Args:
            task: The download task containing URL and metadata
            dest: Destination path for the downloaded file
            progress_callback: Callback function for progress updates

        Raises:
            CurlError: If the download fails
        """
        if task.is_canceled:
            return

        # Prepare
        cmd_headers = [f'-H "{k}: {v}"' for k, v in task.headers.items()]

        # Execute
        with (
            dest.open("wb") as f,
            self.popen_wrapper(self.cmd + self.opt + cmd_headers + [task.url]) as p,
        ):
            try:
                while True:
                    if p.poll() is not None:
                        break
                    if task.is_canceled:
                        break
                    if not p.stdout:
                        break

                    chunk: bytes = p.stdout.read(self.chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    self._handle_progress_callback(
                        progress_callback,
                        task,
                        task.downloaded + len(chunk),
                        task.total,
                    )

            except Exception as e:
                raise CurlError(
                    f"Error downloading {task.url} for {task.dest.name}"
                ) from e
