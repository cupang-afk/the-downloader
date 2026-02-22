"""Callback module for download event handling."""

import traceback
from abc import ABCMeta, abstractmethod
from types import TracebackType
from typing import Any, Protocol

from .logger import logger
from .task import DownloadTask

type ProgressDownloaded = int | float
type ProgressTotal = int | float


class ProgressCallback(Protocol):
    """Protocol for progress callback functions.

    This protocol defines the interface for functions that handle
    download progress updates.
    """

    def __call__(
        self,
        task: DownloadTask,
        downloaded: ProgressDownloaded,
        total: ProgressTotal,
        **extra: Any,
    ) -> None:
        """Called with progress information.

        Args:
            task: The download task being processed.
            downloaded: Number of bytes downloaded so far.
            total: Total number of bytes to download.
            **extra: Additional metadata from the download provider.
        """
        ...


class CallbackNonZeroReturnError(Exception):
    """Raised when a callback function returns a non-None value."""

    pass


class DownloadCallback(metaclass=ABCMeta):
    """Abstract base class for download callbacks.

    Subclasses must implement all abstract methods to handle
    download lifecycle events.
    """

    @abstractmethod
    def on_cancel(self, task: DownloadTask) -> None:
        """Called when a download is cancelled.

        Args:
            task: The download task that was cancelled.
        """
        ...

    @abstractmethod
    def on_complete(self, task: DownloadTask) -> None:
        """Called when a download completes successfully.

        Args:
            task: The download task that completed.
        """
        ...

    @abstractmethod
    def on_error(
        self,
        task: DownloadTask,
        error: tuple[type[BaseException], Exception, TracebackType],
    ) -> None:
        """Called when a download encounters an error.

        Args:
            task: The download task that encountered an error.
            error: A tuple containing (exception_type, exception_instance, traceback).
        """
        ...

    @abstractmethod
    def on_progress(
        self,
        task: DownloadTask,
        downloaded: ProgressDownloaded,
        total: ProgressTotal,
        **extra: Any,
    ) -> None:
        """Called periodically to report download progress.

        Args:
            task: The download task being processed.
            downloaded: Number of bytes downloaded so far.
            total: Total number of bytes to download.
            **extra: Additional metadata from the download provider.
        """
        ...

    @abstractmethod
    def on_start(self, task: DownloadTask) -> None:
        """Called when a download starts.

        Args:
            task: The download task that is starting.
        """
        ...


class DefaultDownloadCallback(DownloadCallback):
    """Default implementation of DownloadCallback that logs events.

    This implementation logs all download events using the module logger.
    """

    def on_cancel(self, task: DownloadTask) -> None:
        """Logs a cancellation message."""
        logger.info(f"Download task {task.url} cancelled")

    def on_complete(self, task: DownloadTask) -> None:
        """Logs a completion message."""
        logger.info(f"Download task {task.url} completed")

    def on_error(
        self,
        task: DownloadTask,
        error: tuple[type[BaseException], Exception, TracebackType],
    ) -> None:
        """Logs an error message with traceback."""
        logger.error(
            f"Download task {task.url} failed with error: {traceback.format_exception(*error)}"
        )

    def on_progress(
        self,
        task: DownloadTask,
        downloaded: ProgressDownloaded,
        total: ProgressTotal,
        **extra: Any,
    ) -> None:
        """Logs progress information."""
        logger.info(
            f"Download task {task.progress_name} progress: {downloaded}/{total}"
        )

    def on_start(self, task: DownloadTask) -> None:
        """Logs a start message."""
        logger.info(f"Download task {task.url} started")
