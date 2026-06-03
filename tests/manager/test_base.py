"""Tests for base manager behavior."""

from abc import ABC
from pathlib import Path, PurePath
from typing import Any, override

import pytest

from the_downloader.callback import BaseCallback
from the_downloader.exceptions import CallbackNonZeroReturnError
from the_downloader.manager.base import BaseManager
from the_downloader.provider import BaseProvider
from the_downloader.task import DownloadStatus, DownloadTask
from the_downloader.types.alias import ExcInfo
from the_downloader.types.protocol import CheckCanceled, UpdateProgress


class CompleteCallback(BaseCallback):
    """Concrete callback for base manager tests."""

    def __init__(self) -> None:
        """Initialize callback calls."""
        self.calls: list[str] = []

    @override
    def on_cancel(self, task: DownloadTask) -> None:
        """Record cancellation."""
        self.calls.append(f"cancel:{task.progress_name}")

    @override
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None:
        """Record error."""
        self.calls.append(f"error:{task.progress_name}:{exc_info[1]}")

    @override
    def on_finish(self, task: DownloadTask) -> None:
        """Record finish."""
        self.calls.append(f"finish:{task.progress_name}")

    @override
    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **optional_data: Any,
    ) -> None:
        """Record progress."""
        self.calls.append(f"progress:{task.progress_name}:{downloaded}:{total}")

    @override
    def on_start(self, task: DownloadTask) -> None:
        """Record start."""
        self.calls.append(f"start:{task.progress_name}")


class CompleteProvider(BaseProvider):
    """Concrete provider for base manager tests."""

    def __init__(self) -> None:
        """Initialize provider calls."""
        super().__init__()
        self.calls: list[str] = []

    @override
    def __post_hook__(self) -> None:
        """Record post hook."""
        self.calls.append("post")

    @override
    def __pre_hook__(self) -> None:
        """Record pre hook."""
        self.calls.append("pre")

    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        """Write fake downloaded content."""
        self.calls.append(f"download:{url}:{dest.name}:{bool(headers)}")
        Path(dest).write_bytes(b"downloaded")
        update_progress(10, 20)


class CompleteManager(BaseManager):
    """Concrete manager for base manager tests."""

    def __init__(self, provider: BaseProvider, callback: BaseCallback) -> None:
        """Initialize manager calls."""
        super().__init__(provider, callback, retry_delay=0)
        self.calls: list[str] = []

    @override
    def add(self, task: DownloadTask) -> None:
        """Record add."""
        self.calls.append(f"add:{task.progress_name}")

    @override
    def cancel(self) -> None:
        """Record cancel."""
        self.calls.append("cancel")

    @override
    def start(self) -> None:
        """Record start."""
        self.calls.append("start")

    @override
    def stop(self) -> None:
        """Record stop."""
        self.calls.append("stop")

    @override
    def wait(self) -> None:
        """Record wait."""
        self.calls.append("wait")


class MissingWaitManager(BaseManager, ABC):
    """Incomplete manager missing one required abstract method."""

    @override
    def add(self, task: DownloadTask) -> None:
        """Handle add."""

    @override
    def cancel(self) -> None:
        """Handle cancel."""

    @override
    def start(self) -> None:
        """Handle start."""

    @override
    def stop(self) -> None:
        """Handle stop."""


def test_base_manager_rejects_direct_instantiation() -> None:
    """Reject direct instantiation because required methods are abstract."""
    manager_type = type("RuntimeBaseManager", (BaseManager,), {})
    provider = CompleteProvider()
    callback = CompleteCallback()

    with pytest.raises(TypeError, match="abstract"):
        manager_type(provider, callback)


def test_base_manager_rejects_incomplete_subclass() -> None:
    """Reject subclasses that do not implement every required method."""
    manager_type = type(
        "RuntimeMissingWaitManager",
        (MissingWaitManager,),
        {},
    )
    provider = CompleteProvider()
    callback = CompleteCallback()

    with pytest.raises(TypeError, match="abstract"):
        manager_type(provider, callback)


def test_base_manager_initializes_with_valid_dependencies() -> None:
    """Store provider, callback, and retry configuration."""
    provider = CompleteProvider()
    callback = CompleteCallback()

    manager = CompleteManager(provider, callback)

    assert manager.provider is provider
    assert manager.callback is callback
    assert manager.retry_delay == 0


def test_base_manager_rejects_invalid_provider() -> None:
    """Reject providers that do not inherit BaseProvider."""
    callback = CompleteCallback()

    with pytest.raises(TypeError, match="provider"):
        CompleteManager(
            object(),  # pyright: ignore[reportArgumentType]
            callback,
        )


def test_base_manager_rejects_invalid_callback() -> None:
    """Reject callbacks that do not inherit BaseCallback."""
    provider = CompleteProvider()

    with pytest.raises(TypeError, match="callback"):
        CompleteManager(
            provider,
            object(),  # pyright: ignore[reportArgumentType]
        )


def test_base_manager_context_manager_runs_hooks() -> None:
    """Run provider hooks around manager start and stop."""
    provider = CompleteProvider()
    callback = CompleteCallback()
    manager = CompleteManager(provider, callback)

    with manager as entered:
        assert entered is manager
        assert provider.calls == ["pre"]
        assert manager.calls == ["start"]

    assert provider.calls == ["pre", "post"]
    assert manager.calls == ["start", "stop"]


def test_base_manager_cancel_task_cancels_pending_task() -> None:
    """Cancel tasks that are not already terminal."""
    manager = CompleteManager(CompleteProvider(), CompleteCallback())
    task = DownloadTask("https://example.com/file.zip", "file.zip")

    manager.cancel_task(task)

    assert task.status is DownloadStatus.CANCELED
    assert task.is_canceled is True


def test_base_manager_cancel_task_ignores_terminal_task() -> None:
    """Ignore tasks that already have a terminal status."""
    manager = CompleteManager(CompleteProvider(), CompleteCallback())
    task = DownloadTask("https://example.com/file.zip", "file.zip")
    task.status = DownloadStatus.FINISHED

    manager.cancel_task(task)

    assert task.status is DownloadStatus.FINISHED
    assert task.is_canceled is False


def test_base_manager_handle_download_finishes_task(tmp_path: Path) -> None:
    """Download a task, move the result, and emit lifecycle callbacks."""
    provider = CompleteProvider()
    callback = CompleteCallback()
    manager = CompleteManager(provider, callback)
    dest = tmp_path / "file.zip"
    task = DownloadTask(
        "https://example.com/file.zip",
        dest,
        progress_name="file",
    )

    manager._handle_download(task)  # pyright: ignore[reportPrivateUsage]

    assert dest.read_bytes() == b"downloaded"
    assert task.status is DownloadStatus.FINISHED
    assert callback.calls == [
        "start:file",
        "progress:file:10:20",
        "finish:file",
    ]


def test_base_manager_handle_callback_rejects_non_zero_return() -> None:
    """Reject callbacks that return non-zero values."""
    manager = CompleteManager(CompleteProvider(), CompleteCallback())

    def callback() -> int:
        """Return non-zero to simulate callback failure."""
        return 1

    with pytest.raises(CallbackNonZeroReturnError):
        manager._handle_callback(  # pyright: ignore[reportPrivateUsage]
            callback,
        )
