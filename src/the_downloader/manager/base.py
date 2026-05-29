"""Base download manager implementation."""

import shutil
from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from logging import Logger
from pathlib import Path, PurePath
from tempfile import NamedTemporaryFile
from types import TracebackType
from typing import Any, Self, final

from ..callback import BaseCallback
from ..exceptions import CallbackNonZeroReturnError, RetryError
from ..provider import BaseProvider
from ..task import DownloadStatus, DownloadTask
from ..types.protocol import BinaryIOProtocol
from ..utils import logger
from ..utils.file import delete
from ..utils.retry import retry


class BaseManager(metaclass=ABCMeta):
    """Base class for download managers.

    This class provides common functionality for managing download tasks,
    including callback handling, retries, and result management.
    """

    def __init__(
        self,
        provider: BaseProvider,
        callback: BaseCallback,
        *,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_backoff_factor: float = 2.0,
    ) -> None:
        """Initializes a BaseManager.

        Args:
            provider: The download provider to use.
            callback: The callback object for monitoring events.
            max_retries: Maximum number of download retries.
            retry_delay: Initial delay between retries in seconds.
            retry_backoff_factor: Multiplier for retry delay after each attempt.

        Raises:
            TypeError: If provider or callback are not of the expected types.
        """
        if not isinstance(provider, BaseProvider):
            raise TypeError("provider must be instance of BaseProvider")
        if not isinstance(callback, BaseCallback):
            raise TypeError("callback must be instance of BaseCallback")

        self.provider: BaseProvider = provider
        self.callback: BaseCallback = callback
        self.max_retries: int = max_retries
        self.retry_delay: float = retry_delay
        self.retry_backoff_factor: float = retry_backoff_factor

    @final
    def get_logger(self) -> Logger:
        """Get the logger for this manager.

        Returns:
            A Logger instance named after the class.
        """
        return logger.get_logger(type(self).__name__)

    # handler
    def _handle_callback[**P, R](
        self,
        func: Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        """Executes a callback function and checks its return value.

        Args:
            func: The callback function to execute.
            *args: Arguments for the callback.
            **kwargs: Keyword arguments for the callback.

        Returns:
            The return value of the callback.

        Raises:
            CallbackNonZeroReturnError: If the callback returns a non-zero value.
        """
        result = func(*args, **kwargs)
        if result is not None and result != 0:
            raise CallbackNonZeroReturnError(f"{func.__name__} return non-zero value")
        return result

    def _handle_result(
        self, tempfile_path: Path, dest: Path | BinaryIOProtocol
    ) -> None:
        """Moves the downloaded file from a temporary location to its destination.

        Args:
            tempfile_path: Path to the temporary file.
            dest: Final destination path or binary file-like object.
        """
        if isinstance(dest, Path):
            shutil.move(tempfile_path, dest)
        else:
            with open(tempfile_path, "rb") as f:
                shutil.copyfileobj(f, dest)

    def _handle_download(self, task: DownloadTask) -> None:
        """Executes the download process for a single task.

        Args:
            task: The download task to process.

        Raises:
            RetryError: If the download fails after all retry attempts.
        """
        _logger: Logger = self.get_logger()
        _logger.info("Downloading %s — %s", task.progress_name, task.url)
        tempfile_path: Path | None = None
        try:
            with NamedTemporaryFile(
                dir=None if not isinstance(task.dest, Path) else task.dest.parent,
                delete=False,
                delete_on_close=False,
            ) as tmp:
                tempfile_path = Path(tmp.name)
            _logger.debug("Tempfile: %s", tempfile_path)

            task.status = DownloadStatus.RUNNING
            self._handle_callback(self.callback.on_start, task)

            @retry(
                max_retries=self.max_retries,
                delay=self.retry_delay,
                backoff_factor=self.retry_backoff_factor,
            )
            def download_handler() -> None:
                def check_canceled() -> bool:
                    return task.is_canceled

                def update_progress(
                    downloaded: int,
                    total: int,
                    **optional_data: Any,
                ) -> None:
                    try:
                        self._handle_callback(
                            self.callback.on_progress,
                            task,
                            downloaded,
                            total,
                            **optional_data,
                        )
                    except CallbackNonZeroReturnError:
                        # cancel task when progress is return non zero
                        # as an alternative way to cancel the task
                        task.cancel()
                        raise

                return self.provider.download(
                    url=task.url,
                    dest=PurePath(tempfile_path),
                    headers=task.headers,
                    check_canceled=check_canceled,
                    update_progress=update_progress,
                )

            retry_result = download_handler()
            if not retry_result.succeeded:
                cause = retry_result.exceptions[-1] if retry_result.exceptions else None
                _logger.error("Failed — %s", task.progress_name)
                raise RetryError(f"Failed to download {task.progress_name}") from cause

            if task.is_canceled:
                _logger.debug("Canceled after download — %s", task.progress_name)
                task.status = DownloadStatus.CANCELED
                self._handle_callback(self.callback.on_cancel, task)
                return

            self._handle_result(tempfile_path, task.dest)
            task.status = DownloadStatus.FINISHED
            _logger.info("Finished — %s", task.progress_name)
            self._handle_callback(self.callback.on_finish, task)
        except KeyboardInterrupt:
            _logger.exception("Interrupted — %s", task.progress_name)
            task.status = DownloadStatus.CANCELED
            self._handle_callback(self.callback.on_cancel, task)
        except Exception as e:
            if task.is_canceled:
                _logger.exception("Canceled download")
                task.status = DownloadStatus.CANCELED
                self._handle_callback(self.callback.on_cancel, task)
            else:
                _logger.exception("Download failed")
                task.status = DownloadStatus.ERROR
                self._handle_callback(
                    self.callback.on_error, task, (type(e), e, e.__traceback__)
                )

        finally:
            if tempfile_path is not None and tempfile_path.exists():
                _logger.debug("Removing tempfile: %s", tempfile_path)
                delete(tempfile_path)

    # abstract method
    @abstractmethod
    def start(self) -> None:
        """Starts the download manager."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stops the download manager."""
        ...

    @abstractmethod
    def cancel(self) -> None:
        """Cancels all active downloads in the manager."""
        ...

    @abstractmethod
    def add(self, task: DownloadTask) -> None:
        """Adds a download task to the manager.

        Args:
            task: The download task to add.
        """
        ...

    @abstractmethod
    def wait(self) -> None:
        """Waits for all added tasks to complete."""
        ...

    @final
    def cancel_task(self, task: DownloadTask) -> None:
        """Cancels a specific download task.

        Args:
            task: The download task to cancel.
        """
        if task.status not in (
            DownloadStatus.CANCELED,
            DownloadStatus.FINISHED,
            DownloadStatus.ERROR,
        ):
            task.cancel()

    @final
    def __enter__(self) -> Self:
        """Enters the context manager, starting the manager and provider hooks.

        Returns:
            The manager instance itself.
        """
        self.provider.__pre_hook__()
        self.start()
        return self

    @final
    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        """Exits the context manager, stopping the manager and provider hooks.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value.
            exc_tb: Exception traceback.
        """
        self.stop()
        self.provider.__post_hook__()
