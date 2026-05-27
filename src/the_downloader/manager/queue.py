"""Parallel download manager implementation."""

import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event, Lock
from typing import override

from ..callback import BaseCallback
from ..provider import BaseProvider
from ..task import DownloadTask
from .base import BaseManager


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
