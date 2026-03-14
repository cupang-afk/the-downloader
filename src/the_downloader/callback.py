import traceback
from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from typing import Any

from .error import CallbackError, CallbackNonZeroReturnError
from .task import DownloadTask
from .types import ExcInfo, ProgressDownloaded, ProgressTotal


def handle_callback[**P, R](
    callback: Callable[P, R], *args: P.args, **kwargs: P.kwargs
) -> R:
    """Handle a callback function with error handling and validation.

    Args:
        callback: The callback function to execute
        *args: Positional arguments to pass to the callback
        **kwargs: Keyword arguments to pass to the callback

    Returns:
        The result of the callback function

    Raises:
        TypeError: If callback is not callable
        CallbackNonZeroReturnError: If callback returns a non-zero value
        CallbackError: If callback raises an exception
    """
    if not callable(callback):
        raise TypeError("callback must be callable")
    callback_name = getattr(callback, "__name__", str(callback))
    try:
        result = callback(*args, **kwargs)
        if result is not None and result != 0:
            raise CallbackNonZeroReturnError(
                f"Callback {callback_name!r} returned {result!r}, expected None or 0"
            )
        return result
    except Exception as e:
        raise CallbackError(
            f"Callback {callback_name!r} raised an exception: {e}"
        ) from e


class DownloadCallback(metaclass=ABCMeta):
    """Define an abstract base class for download callbacks.

    Defines the interface for handling download progress and events.
    Implementations must provide methods for handling download start, progress,
    completion, cancellation, and error events.
    """

    def __pre_start__(self) -> None:
        """Perform actions before the callback starts.

        This hook is called before the downloader enters its running state.
        Subclasses may override this to initialize resources, start external
        processes, or perform other setup operations.
        """
        return

    def __post_stop__(self) -> None:
        """Perform actions after the callback stops.

        This hook is called after the downloader exits its running state.
        Subclasses may override this to release resources, terminate external
        processes, or perform other cleanup operations.
        """
        return

    @abstractmethod
    def on_cancel(self, task: DownloadTask) -> None:
        """Handle download cancellation.

        Args:
            task: The canceled download task
        """

    @abstractmethod
    def on_complete(self, task: DownloadTask) -> None:
        """Handle download completion.

        Args:
            task: The completed download task
        """

    @abstractmethod
    def on_error(
        self,
        task: DownloadTask,
        error: ExcInfo,
    ) -> None:
        """Handle download error.

        Args:
            task: The download task that encountered an error
            error: Exception information (type, value, traceback)
        """

    @abstractmethod
    def on_progress(
        self,
        task: DownloadTask,
        downloaded: ProgressDownloaded,
        total: ProgressTotal,
        **extra: Any,
    ) -> None:
        """Handle download progress update.

        Args:
            task: The download task
            downloaded: Number of bytes downloaded so far
            total: Total number of bytes to download
            **extra: Additional progress information
        """

    @abstractmethod
    def on_start(self, task: DownloadTask) -> None:
        """Handle download start.

        Args:
            task: The download task that started
        """


class DefaultDownloadCallback(DownloadCallback):
    """Provide a default implementation of DownloadCallback for basic progress tracking.

    Provides a simple implementation that prints download events to stdout
    for debugging and basic monitoring purposes.
    """

    def on_cancel(self, task: DownloadTask) -> None:
        """Handle download cancellation by printing a message.

        Args:
            task: The canceled download task
        """
        print(f"Download task {task.progress_name} cancelled")

    def on_complete(self, task: DownloadTask) -> None:
        """Handle download completion by printing a message.

        Args:
            task: The completed download task
        """
        print(f"Download task {task.progress_name} completed")

    def on_error(
        self,
        task: DownloadTask,
        error: ExcInfo,
    ) -> None:
        """Handle download error by printing error details.

        Args:
            task: The download task that encountered an error
            error: Exception information (type, value, traceback)
        """
        print(
            f"Download task {task.progress_name} failed with error: "
            f"{traceback.format_exception(*error)}"
        )

    def on_progress(
        self,
        task: DownloadTask,
        downloaded: ProgressDownloaded,
        total: ProgressTotal,
        **extra: Any,
    ) -> None:
        """Handle download progress by printing progress information.

        Args:
            task: The download task
            downloaded: Number of bytes downloaded so far
            total: Total number of bytes to download
            **extra: Additional progress information
        """
        print(f"Download task {task.progress_name} progress: {downloaded}/{total}")

    def on_start(self, task: DownloadTask) -> None:
        """Handle download start by printing a message.

        Args:
            task: The download task that started
        """
        print(f"Download task {task.progress_name} started")
