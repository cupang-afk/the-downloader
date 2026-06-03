"""Tests for builtin queue download manager behavior."""

from pathlib import PurePath
from typing import override

import pytest

from the_downloader.callback import NullDownloadCallback
from the_downloader.manager.queue import QueueDownloadManager
from the_downloader.provider import BaseProvider
from the_downloader.task import DownloadStatus, DownloadTask
from the_downloader.types.protocol import CheckCanceled, UpdateProgress


class NoOpProvider(BaseProvider):
    """Provider that completes downloads without touching the filesystem."""

    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        """Report progress unless canceled."""
        if check_canceled():
            return
        update_progress(1, 1)


class RecordingQueueManager(QueueDownloadManager):
    """Queue manager that records handled tasks without downloading."""

    def __init__(self) -> None:
        """Initialize the recording manager."""
        super().__init__(NoOpProvider(), NullDownloadCallback(), max_workers=1)
        self.handled: list[str] = []

    @override
    def _handle_download(self, task: DownloadTask) -> None:
        """Record the handled task."""
        self.handled.append(task.progress_name)


def test_queue_download_manager_rejects_add_before_start() -> None:
    """Reject adding tasks before the manager is started."""
    manager = RecordingQueueManager()
    task = DownloadTask("https://example.com/file.zip", "file.zip")

    with pytest.raises(RuntimeError, match="not running"):
        manager.add(task)


def test_queue_download_manager_rejects_stop_before_start() -> None:
    """Reject stopping before the manager is started."""
    manager = RecordingQueueManager()

    with pytest.raises(RuntimeError, match="not running"):
        manager.stop()


def test_queue_download_manager_rejects_duplicate_start() -> None:
    """Reject starting an already running manager."""
    manager = RecordingQueueManager()
    manager.start()

    with pytest.raises(RuntimeError, match="already running"):
        manager.start()

    manager.stop()


def test_queue_download_manager_add_submits_task() -> None:
    """Submit added tasks to the running thread pool."""
    manager = RecordingQueueManager()
    task = DownloadTask("https://example.com/file.zip", "file.zip")
    manager.start()

    manager.add(task)
    manager.wait()
    manager.stop()

    assert manager.handled == ["file.zip"]


def test_queue_download_manager_cancel_marks_tasks() -> None:
    """Cancel active or queued tasks."""
    manager = RecordingQueueManager()
    task = DownloadTask("https://example.com/file.zip", "file.zip")
    manager.start()
    manager.add(task)

    manager.cancel()
    manager.stop()

    assert task.status is DownloadStatus.CANCELED
    assert task.is_canceled is True


def test_queue_download_manager_context_starts_and_stops() -> None:
    """Start and stop the thread pool around a context manager block."""
    manager = RecordingQueueManager()

    with manager as entered:
        assert entered is manager
        threadpool = manager._threadpool  # pyright: ignore[reportPrivateUsage]
        assert threadpool is not None

    assert manager._threadpool is None  # pyright: ignore[reportPrivateUsage]
