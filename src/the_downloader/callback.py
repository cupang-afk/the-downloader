"""Download callback interfaces and implementations.

This module defines the base callback class and a basic implementation for
monitoring download progress and state changes.
"""

from abc import ABCMeta, abstractmethod
from typing import Any, override

from .task import DownloadTask
from .types.alias import ExcInfo


class BaseCallback(metaclass=ABCMeta):
    """Base class for download callbacks.

    All download callbacks should inherit from this class and implement the
    required methods to handle various download events.
    """

    @abstractmethod
    def on_cancel(self, task: DownloadTask) -> None:
        """Called when a download task is canceled.

        Args:
            task: The download task that was canceled.
        """
        ...

    @abstractmethod
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None:
        """Called when a download task encounters an error.

        Args:
            task: The download task that encountered an error.
            exc_info: Exception information (type, value, traceback).
        """
        ...

    @abstractmethod
    def on_finish(self, task: DownloadTask) -> None:
        """Called when a download task finishes successfully.

        Args:
            task: The download task that has finished.
        """
        ...

    @abstractmethod
    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **optional_data: Any,
    ) -> None:
        """Called to update the progress of a download task.

        Args:
            task: The download task being updated.
            downloaded: Number of bytes downloaded so far.
            total: Total number of bytes to download.
            **optional_data: Additional provider-specific progress information.
        """
        ...

    @abstractmethod
    def on_start(self, task: DownloadTask) -> None:
        """Called when a download task starts.

        Args:
            task: The download task that has started.
        """
        ...


class BasicDownloadCallback(BaseCallback):
    """A basic download callback that prints progress to stdout.

    This implementation provides a simple way to monitor downloads in a terminal.
    """

    def __init__(self) -> None:
        """Initializes the BasicDownloadCallback."""
        self._template: str = "Download Status of {progress_name}: {message}"

    @override
    def on_cancel(self, task: DownloadTask) -> None:
        """Prints a message when the download is canceled.

        Args:
            task: The download task that was canceled.
        """
        print(
            self._template.format(
                progress_name=task.progress_name,
                message="canceled",
            ),
            flush=True,
        )

    @override
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None:
        """Prints an error message when the download fails.

        Args:
            task: The download task that encountered an error.
            exc_info: Exception information.
        """
        print(
            self._template.format(
                progress_name=task.progress_name,
                message=f"error: {exc_info}",
            ),
            flush=True,
        )

    @override
    def on_finish(self, task: DownloadTask) -> None:
        """Prints a message when the download finishes.

        Args:
            task: The download task that has finished.
        """
        print(
            self._template.format(
                progress_name=task.progress_name,
                message="finished",
            ),
            flush=True,
        )

    @override
    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **optional_data: Any,
    ) -> None:
        """Prints progress updates during download.

        Args:
            task: The download task being updated.
            downloaded: Number of bytes downloaded.
            total: Total number of bytes.
            **optional_data: Additional information.
        """
        percent = (downloaded / total * 100) if total > 0 else 0.0
        print(
            self._template.format(
                progress_name=task.progress_name,
                message=f"progress {percent:.2f}% ({downloaded}/{total} bytes)"
                if total > 0
                else f"progress {downloaded} bytes",
            ),
            flush=True,
        )

    @override
    def on_start(self, task: DownloadTask) -> None:
        """Prints a message when the download starts.

        Args:
            task: The download task that has started.
        """
        print(
            self._template.format(
                progress_name=task.progress_name,
                message="started",
            ),
            flush=True,
        )


class NullDownloadCallback(BaseCallback):
    """A download callback that ignores all events."""

    @override
    def on_cancel(self, task: DownloadTask) -> None:
        """Ignore a download cancellation event."""
        pass

    @override
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None:
        """Ignore a download error event."""
        pass

    @override
    def on_finish(self, task: DownloadTask) -> None:
        """Ignore a download finish event."""
        pass

    @override
    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **optional_data: Any,
    ) -> None:
        """Ignore a download progress event."""
        pass

    @override
    def on_start(self, task: DownloadTask) -> None:
        """Ignore a download start event."""
        pass
