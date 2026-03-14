from os import PathLike
from types import TracebackType
from typing import Any, BinaryIO, Protocol

from .task import DownloadTask

# Type aliases for common values
type DestPathOrObject = str | PathLike[str] | BinaryIO
type ExcInfo = tuple[type[BaseException], BaseException, TracebackType | None]
type Overwrite = bool
type ProgressDownloaded = int
type ProgressTotal = int


class StartCallback(Protocol):
    """Define a protocol for download start callback functions.

    Callback functions that implement this protocol are called when a download
    task starts.
    """

    def __call__(self, task: DownloadTask) -> None:
        """Callback function to be called when a download task starts.

        Args:
            task: The download task that is starting
        """
        ...


class CompleteCallback(Protocol):
    """Define a protocol for download completion callback functions.

    Callback functions that implement this protocol are called when a download
    task completes successfully.
    """

    def __call__(self, task: DownloadTask) -> None:
        """Callback function to be called when a download task completes successfully.

        Args:
            task: The download task that completed successfully
        """
        ...


class CancelCallback(Protocol):
    """Define a protocol for download cancellation callback functions.

    Callback functions that implement this protocol are called when a download
    task is canceled.
    """

    def __call__(self, task: DownloadTask) -> None:
        """Callback function to be called when a download task is canceled.

        Args:
            task: The download task that was canceled
        """
        ...


class ErrorCallback(Protocol):
    """Define a protocol for download error callback functions.

    Callback functions that implement this protocol are called when a download
    task encounters an error.
    """

    def __call__(
        self,
        task: DownloadTask,
        error: ExcInfo,
    ) -> None:
        """Callback function to be called when a download task encounters an error.

        Args:
            task: The download task that encountered the error
            error: The error information
        """
        ...


class ProgressCallback(Protocol):
    """Define a protocol for download progress callback functions.

    Callback functions that implement this protocol are called periodically
    during a download to report progress.
    """

    def __call__(
        self,
        task: DownloadTask,
        downloaded: ProgressDownloaded,
        total: ProgressTotal,
        **extra: Any,
    ) -> None:
        """Callback function called periodically to report download progress.

        Args:
            task: The download task being processed
            downloaded: The number of bytes downloaded so far
            total: The total number of bytes to download
            extra: Additional data provided by the download provider
        """
        ...
