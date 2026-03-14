from pathlib import Path

from ..constants import CA_CERT_PATH
from ..error import ProviderError
from ..http_session import get_session
from ..task import DownloadTask
from ..types import ProgressCallback
from .base import DownloadProvider


class RequestsError(ProviderError):
    """Represent an error class for Requests download provider exceptions."""

    pass


class RequestsDownloader(DownloadProvider):
    """Implement a requests download provider."""

    def download(
        self,
        task: DownloadTask,
        dest: Path,
        progress_callback: ProgressCallback,
    ) -> None:
        """Download a file using the requests library.

        Args:
            task: The download task containing URL and metadata
            dest: Destination path for the downloaded file
            progress_callback: Callback function for progress updates
        """
        if task.is_canceled:
            return

        # Execute
        with (
            dest.open("wb") as f,
            get_session().get(
                task.url,
                headers=task.headers,
                stream=True,
                verify=CA_CERT_PATH,  # type: ignore
            ) as res,
        ):
            res.raise_for_status()

            try:
                for chunk in res.iter_content(chunk_size=self.chunk_size):
                    if task.is_canceled:
                        break
                    if not chunk:
                        continue
                    f.write(chunk)
                    self._handle_progress_callback(
                        progress_callback,
                        task,
                        task.downloaded + len(chunk),
                        task.total,
                    )
            except Exception as e:
                raise RequestsError(
                    f"Error downloading {task.url} for {task.dest.name}"
                ) from e
