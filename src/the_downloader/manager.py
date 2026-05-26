import shutil
from abc import ABCMeta, abstractmethod
from collections import deque
from pathlib import Path, PurePath
from tempfile import NamedTemporaryFile
from threading import Event
from types import TracebackType
from typing import Any, Callable, Self, final, override

from .callback import BaseCallback
from .constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF_FACTOR,
    DEFAULT_RETRY_DELAY,
)
from .exceptions import CallbackNonZeroReturnError, RetryError
from .provider import BaseProvider
from .task import DownloadStatus, DownloadTask
from .types.protocol import BinaryIOProtocol
from .utils.file import delete
from .utils.retry import retry


class BaseManager(metaclass=ABCMeta):
    def __init__(
        self,
        provider: BaseProvider,
        callback: BaseCallback,
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        retry_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR,
    ) -> None:
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
        result = func(*args, **kwargs)
        if result is not None and result != 0:
            raise CallbackNonZeroReturnError(f"{func.__name__} return non-zero value")
        return result

    def _handle_result(
        self, tempfile_path: Path, dest: Path | BinaryIOProtocol
    ) -> None:
        if isinstance(dest, Path):
            shutil.move(tempfile_path, dest)
        else:
            with open(tempfile_path, "rb") as f:
                shutil.copyfileobj(f, dest)

    def _handle_download(self, task: DownloadTask):
        tempfile_path: Path | None = None
        try:
            with NamedTemporaryFile(
                dir=None if not isinstance(task.dest, Path) else task.dest.parent,
                delete=False,
                delete_on_close=False,
            ) as tmp:
                tempfile_path = Path(tmp.name)

            with task.lock():
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
                with task.lock():
                    task.status = DownloadStatus.CANCELED
                self._handle_callback(self.callback.on_cancel, task)
                return

            self._handle_result(tempfile_path, task.dest)
            with task.lock():
                task.status = DownloadStatus.FINISHED
            self._handle_callback(self.callback.on_finish, task)
        except KeyboardInterrupt:
            with task.lock():
                task.status = DownloadStatus.CANCELED
            self._handle_callback(self.callback.on_cancel, task)
        except Exception as e:
            if task.is_canceled:
                with task.lock():
                    task.status = DownloadStatus.CANCELED
                self._handle_callback(self.callback.on_cancel, task)
            else:
                with task.lock():
                    task.status = DownloadStatus.ERROR
                self._handle_callback(
                    self.callback.on_error, task, (type(e), e, e.__traceback__)
                )

        finally:
            if tempfile_path is not None and tempfile_path.exists():
                delete(tempfile_path)

    # abstract method
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def cancel(self) -> None: ...
    @abstractmethod
    def add(self, task: DownloadTask) -> None: ...
    @abstractmethod
    def wait(self) -> None: ...

    @final
    def cancel_task(self, task: DownloadTask) -> None:
        with task.lock():
            if task.status not in (
                DownloadStatus.CANCELED,
                DownloadStatus.FINISHED,
                DownloadStatus.ERROR,
            ):
                task.cancel()

    @final
    def __enter__(self) -> Self:
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
        self.stop()
        self.provider.__post_hook__()


class BasicDownloadManager(BaseManager):
    def __init__(
        self,
        provider: BaseProvider,
        callback: BaseCallback,
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        retry_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR,
    ) -> None:
        super().__init__(
            provider,
            callback,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_backoff_factor=retry_backoff_factor,
        )
        self._simple_queue: deque[DownloadTask] = deque()
        self._running: Event = Event()

    @override
    def start(self) -> None:
        if self._running.is_set():
            raise RuntimeError("DownloadManager is already running")
        self._running.set()

    @override
    def stop(self) -> None:
        if not self._running.is_set():
            raise RuntimeError("DownloadManager is not running")
        self._running.clear()

    @override
    def cancel(self) -> None:
        if not self._running.is_set():
            raise RuntimeError("DownloadManager is not running")
        for task in self._simple_queue:
            task.cancel()

    @override
    def add(self, task: DownloadTask) -> None:
        if not self._running.is_set():
            raise RuntimeError("DownloadManager is not running")
        self._simple_queue.append(task)

    @override
    def wait(self) -> None:
        if not self._running.is_set():
            raise RuntimeError("DownloadManager is not running")
        while self._simple_queue:
            # cSpell: words popleft
            task = self._simple_queue.popleft()
            self._handle_download(task)
