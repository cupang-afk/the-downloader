"""Download manager implementations.

This module provides different download manager classes for handling downloads
sequentially or in parallel using a thread pool.
"""

import shutil
import time
from abc import ABCMeta, abstractmethod
from collections import deque
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path, PurePath
from tempfile import NamedTemporaryFile
from threading import Event, Lock
from types import TracebackType
from typing import Any, Self, final, override

from .callback import BaseCallback
from .exceptions import CallbackNonZeroReturnError, RetryError
from .provider import BaseProvider
from .task import DownloadStatus, DownloadTask
from .types.protocol import BinaryIOProtocol
from .utils.file import delete
from .utils.retry import retry


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
        tempfile_path: Path | None = None
        try:
            with NamedTemporaryFile(
                dir=None if not isinstance(task.dest, Path) else task.dest.parent,
                delete=False,
                delete_on_close=False,
            ) as tmp:
                tempfile_path = Path(tmp.name)

            task.status = DownloadStatus.RUNNING
            self._handle_callback(self.callback.on_start, task)

            @retry(
                max_retries=self.max_retries,
                delay=self.retry_delay,
                backoff_factor=self.retry_backoff_factor,
            )
            def handler() -> None:
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

            retry_result = handler()
            if not retry_result.succeeded:
                cause = retry_result.exceptions[-1] if retry_result.exceptions else None
                raise RetryError(f"Failed to download {task.progress_name}") from cause

            if task.is_canceled:
                task.status = DownloadStatus.CANCELED
                self._handle_callback(self.callback.on_cancel, task)
                return

            self._handle_result(tempfile_path, task.dest)
            task.status = DownloadStatus.FINISHED
            self._handle_callback(self.callback.on_finish, task)
        except KeyboardInterrupt:
            task.status = DownloadStatus.CANCELED
            self._handle_callback(self.callback.on_cancel, task)
        except Exception as e:
            if task.is_canceled:
                task.status = DownloadStatus.CANCELED
                self._handle_callback(self.callback.on_cancel, task)
            else:
                task.status = DownloadStatus.ERROR
                self._handle_callback(
                    self.callback.on_error, task, (type(e), e, e.__traceback__)
                )

        finally:
            if tempfile_path is not None and tempfile_path.exists():
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


class BasicDownloadManager(BaseManager):
    """A sequential download manager.

    This manager processes download tasks one by one in the order they were added.
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
        """Initializes a BasicDownloadManager.

        Args:
            provider: The download provider.
            callback: The download callback.
            max_retries: Maximum number of retries per task.
            retry_delay: Delay between retries.
            retry_backoff_factor: Backoff factor for retries.
        """
        super().__init__(
            provider,
            callback,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_backoff_factor=retry_backoff_factor,
        )
        self._queue: deque[DownloadTask] = deque()
        self._running: Event = Event()

    @override
    def start(self) -> None:
        """Starts the manager.

        Raises:
            RuntimeError: If the manager is already running.
        """
        if self._running.is_set():
            raise RuntimeError("DownloadManager is already running")
        self._running.set()

    @override
    def stop(self) -> None:
        """Stops the manager.

        Raises:
            RuntimeError: If the manager is not running.
        """
        if not self._running.is_set():
            raise RuntimeError("DownloadManager is not running")
        self._running.clear()

    @override
    def cancel(self) -> None:
        """Cancels all queued tasks.

        Raises:
            RuntimeError: If the manager is not running.
        """
        if not self._running.is_set():
            raise RuntimeError("DownloadManager is not running")
        for task in self._queue:
            task.cancel()

    @override
    def add(self, task: DownloadTask) -> None:
        """Adds a task to the queue.

        Args:
            task: The task to add.

        Raises:
            RuntimeError: If the manager is not running.
        """
        if not self._running.is_set():
            raise RuntimeError("DownloadManager is not running")
        self._queue.append(task)

    @override
    def wait(self) -> None:
        """Processes all tasks in the queue sequentially.

        Raises:
            RuntimeError: If the manager is not running.
        """
        if not self._running.is_set():
            raise RuntimeError("DownloadManager is not running")
        while self._queue:
            # cSpell: words popleft
            task = self._queue.popleft()
            self._handle_download(task)


class QueueDownloadManager(BaseManager):
    """A parallel download manager using a thread pool.

    This manager allows multiple downloads to occur simultaneously up to
    a specified maximum number of workers.
    """

    def __init__(
        self,
        provider: BaseProvider,
        callback: BaseCallback,
        *,
        max_workers: int = 4,
        max_retries: int = 3,
        retry_delay: float = 1,
        retry_backoff_factor: float = 2,
    ) -> None:
        """Initializes a QueueDownloadManager.

        Args:
            provider: The download provider.
            callback: The download callback.
            max_workers: Maximum number of parallel downloads.
            max_retries: Maximum number of retries per task.
            retry_delay: Delay between retries.
            retry_backoff_factor: Backoff factor for retries.
        """
        super().__init__(
            provider,
            callback,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_backoff_factor=retry_backoff_factor,
        )
        self._threadpool: ThreadPoolExecutor | None = None
        self._queue: deque[tuple[DownloadTask, Future[None]]] = deque()
        self._max_workers: int = max_workers

    @override
    def start(self) -> None:
        """Starts the manager and its thread pool.

        Raises:
            RuntimeError: If the manager is already running.
        """
        if self._threadpool is not None:
            raise RuntimeError("DownloadManager is already running")
        self._threadpool = ThreadPoolExecutor(max_workers=self._max_workers)
        self._queue.clear()

    @override
    def stop(self) -> None:
        """Shuts down the manager and its thread pool.

        Raises:
            RuntimeError: If the manager is not running.
        """
        if self._threadpool is None:
            raise RuntimeError("DownloadManager is not running")
        self._threadpool.shutdown(wait=True)
        self._threadpool = None
        self._queue.clear()

    @override
    def add(self, task: DownloadTask) -> None:
        """Submits a task to the thread pool for execution.

        Args:
            task: The task to add.

        Raises:
            RuntimeError: If the manager is not running.
        """
        if self._threadpool is None:
            raise RuntimeError("DownloadManager is not running")
        if not isinstance(task._lock, Lock):  # pyright: ignore[reportPrivateUsage]
            task.set_lock(Lock())
        if not isinstance(task._cancel_event, Event):  # pyright: ignore[reportPrivateUsage]
            task.set_cancel_event(Event())
        self._queue.append((task, self._threadpool.submit(self._handle_download, task)))

    @override
    def cancel(self) -> None:
        """Cancels all active and queued tasks.

        Raises:
            RuntimeError: If the manager is not running.
        """
        if self._threadpool is None:
            raise RuntimeError("DownloadManager is not running")
        for task, future in self._queue:
            task.cancel()
            future.cancel()

    @override
    def wait(self) -> None:
        """Waits for all submitted tasks to complete.

        Raises:
            RuntimeError: If the manager is not running.
        """
        if self._threadpool is None:
            raise RuntimeError("DownloadManager is not running")
        try:
            while not all(future.done() for _, future in self._queue):
                time.sleep(1)
        except KeyboardInterrupt:
            self.cancel()
