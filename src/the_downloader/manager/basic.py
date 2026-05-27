"""Sequential download manager implementation."""

from collections import deque
from threading import Event
from typing import override

from ..callback import BaseCallback
from ..provider import BaseProvider
from ..task import DownloadTask
from .base import BaseManager


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
