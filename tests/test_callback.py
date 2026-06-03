"""Tests for download callback behavior."""

from abc import ABC
from typing import Any, override

import pytest

from the_downloader.callback import BaseCallback
from the_downloader.task import DownloadTask
from the_downloader.types.alias import ExcInfo


class CompleteCallback(BaseCallback):
    """Concrete callback used to test the base callback contract."""

    def __init__(self) -> None:
        """Initialize the callback call log."""
        self.calls: list[str] = []

    @override
    def on_cancel(self, task: DownloadTask) -> None:
        """Record a cancellation callback."""
        self.calls.append(f"cancel:{task.progress_name}")

    @override
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None:
        """Record an error callback."""
        self.calls.append(f"error:{task.progress_name}:{exc_info[1]}")

    @override
    def on_finish(self, task: DownloadTask) -> None:
        """Record a finish callback."""
        self.calls.append(f"finish:{task.progress_name}")

    @override
    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **optional_data: Any,
    ) -> None:
        """Record a progress callback."""
        self.calls.append(
            (
                f"progress:{task.progress_name}:"
                f"{downloaded}:{total}:{optional_data}"
            ),
        )

    @override
    def on_start(self, task: DownloadTask) -> None:
        """Record a start callback."""
        self.calls.append(f"start:{task.progress_name}")


class MissingStartCallback(BaseCallback, ABC):
    """Incomplete callback missing one required callback method."""

    @override
    def on_cancel(self, task: DownloadTask) -> None:
        """Handle cancellation."""

    @override
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None:
        """Handle errors."""

    @override
    def on_finish(self, task: DownloadTask) -> None:
        """Handle finish."""

    @override
    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **optional_data: Any,
    ) -> None:
        """Handle progress."""


def test_base_callback_rejects_direct_instantiation() -> None:
    """Reject direct instantiation because required methods are abstract."""
    callback_type = type("RuntimeBaseCallback", (BaseCallback,), {})

    with pytest.raises(TypeError, match="abstract"):
        callback_type()


def test_base_callback_rejects_incomplete_subclass() -> None:
    """Reject subclasses that do not implement every required method."""
    callback_type = type(
        "RuntimeMissingStartCallback",
        (MissingStartCallback,),
        {},
    )

    with pytest.raises(TypeError, match="abstract"):
        callback_type()


def test_base_callback_accepts_complete_subclass() -> None:
    """Allow subclasses that implement every required callback method."""
    callback = CompleteCallback()
    task = DownloadTask(
        "https://example.com/file.zip",
        "file.zip",
        progress_name="file",
    )
    error = RuntimeError("boom")
    exc_info: ExcInfo = (RuntimeError, error, error.__traceback__)

    callback.on_start(task)
    callback.on_progress(task, 5, 10, provider="fake")
    callback.on_finish(task)
    callback.on_cancel(task)
    callback.on_error(task, exc_info)

    assert callback.calls == [
        "start:file",
        "progress:file:5:10:{'provider': 'fake'}",
        "finish:file",
        "cancel:file",
        "error:file:boom",
    ]
