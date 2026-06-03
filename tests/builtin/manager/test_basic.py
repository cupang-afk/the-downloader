"""Tests for builtin sequential download manager behavior."""

from pathlib import Path, PurePath
from typing import override

import pytest

from the_downloader.callback import NullDownloadCallback
from the_downloader.manager.basic import BasicDownloadManager
from the_downloader.provider import BaseProvider
from the_downloader.task import DownloadStatus, DownloadTask
from the_downloader.types.protocol import CheckCanceled, UpdateProgress


class RecordingProvider(BaseProvider):
    """Provider that writes fake content and records downloads."""

    def __init__(self) -> None:
        """Initialize provider calls."""
        super().__init__()
        self.urls: list[str] = []

    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        """Write fake content unless the task is canceled."""
        self.urls.append(url)
        if check_canceled():
            return
        content = f"downloaded:{url}:{bool(headers)}"
        Path(dest).write_text(content, encoding="utf-8")
        update_progress(1, 1)


class RecordingManager(BasicDownloadManager):
    """Sequential manager that records handled tasks without downloading."""

    def __init__(self) -> None:
        """Initialize the recording manager."""
        super().__init__(RecordingProvider(), NullDownloadCallback())
        self.handled: list[str] = []

    @override
    def _handle_download(self, task: DownloadTask) -> None:
        """Record the handled task."""
        self.handled.append(task.progress_name)


def test_basic_download_manager_rejects_add_before_start() -> None:
    """Reject adding tasks before the manager is started."""
    manager = RecordingManager()
    task = DownloadTask("https://example.com/file.zip", "file.zip")

    with pytest.raises(RuntimeError, match="not running"):
        manager.add(task)


def test_basic_download_manager_rejects_stop_before_start() -> None:
    """Reject stopping before the manager is started."""
    manager = RecordingManager()

    with pytest.raises(RuntimeError, match="not running"):
        manager.stop()


def test_basic_download_manager_rejects_duplicate_start() -> None:
    """Reject starting an already running manager."""
    manager = RecordingManager()
    manager.start()

    with pytest.raises(RuntimeError, match="already running"):
        manager.start()


def test_basic_download_manager_wait_processes_tasks_in_order() -> None:
    """Process queued tasks sequentially in insertion order."""
    manager = RecordingManager()
    first = DownloadTask(
        "https://example.com/first.zip",
        "first.zip",
        progress_name="first",
    )
    second = DownloadTask(
        "https://example.com/second.zip",
        "second.zip",
        progress_name="second",
    )
    manager.start()

    manager.add(first)
    manager.add(second)
    manager.wait()

    assert manager.handled == ["first", "second"]


def test_basic_download_manager_cancel_marks_queued_tasks() -> None:
    """Cancel all queued tasks."""
    manager = RecordingManager()
    task = DownloadTask("https://example.com/file.zip", "file.zip")
    manager.start()
    manager.add(task)

    manager.cancel()

    assert task.status is DownloadStatus.CANCELED
    assert task.is_canceled is True


def test_basic_download_manager_downloads_with_context(tmp_path: Path) -> None:
    """Download queued tasks when used as a context manager."""
    provider = RecordingProvider()
    callback = NullDownloadCallback()
    dest = tmp_path / "file.zip"
    task = DownloadTask("https://example.com/file.zip", dest)

    with BasicDownloadManager(provider, callback, retry_delay=0) as manager:
        manager.add(task)
        manager.wait()

    assert provider.urls == ["https://example.com/file.zip"]
    assert dest.read_text(encoding="utf-8").startswith("downloaded:")
    assert task.status is DownloadStatus.FINISHED
