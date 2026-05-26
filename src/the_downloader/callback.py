from abc import ABCMeta, abstractmethod
from typing import Any, override

from .task import DownloadTask
from .types.alias import ExcInfo


class BaseCallback(metaclass=ABCMeta):
    @abstractmethod
    def on_start(self, task: DownloadTask) -> None: ...

    @abstractmethod
    def on_finish(self, task: DownloadTask) -> None: ...

    @abstractmethod
    def on_cancel(self, task: DownloadTask) -> None: ...

    @abstractmethod
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None: ...

    @abstractmethod
    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **optional_data: Any,
    ) -> None: ...


class BasicDownloadCallback(BaseCallback):
    def __init__(self) -> None:
        self._template: str = "Download Status of {progress_name}: {message}"

    @override
    def on_start(self, task: DownloadTask) -> None:
        print(
            self._template.format(
                progress_name=task.progress_name,
                message="started",
            ),
            flush=True,
        )

    @override
    def on_finish(self, task: DownloadTask) -> None:
        print(
            self._template.format(
                progress_name=task.progress_name,
                message="finished",
            ),
            flush=True,
        )

    @override
    def on_cancel(self, task: DownloadTask) -> None:
        print(
            self._template.format(
                progress_name=task.progress_name,
                message="canceled",
            ),
            flush=True,
        )

    @override
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None:
        print(
            self._template.format(
                progress_name=task.progress_name,
                message=f"error: {exc_info}",
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
