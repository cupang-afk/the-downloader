"""Tests for download task behavior."""

from pathlib import Path
from types import TracebackType

import pytest

from the_downloader.task import (
    DEFAULT_HEADERS,
    DownloadStatus,
    DownloadTask,
    DummyLock,
)


class FakeEvent:
    """Minimal event object for task cancellation tests."""

    def __init__(self) -> None:
        """Initialize the fake event."""
        self.cleared: bool = False
        self.set_calls: int = 0

    def clear(self) -> None:
        """Record that the event was cleared."""
        self.cleared = True

    def is_set(self) -> bool:
        """Return whether the event was set."""
        return self.set_calls > 0

    def set(self) -> None:
        """Record that the event was set."""
        self.set_calls += 1


class FakeLock:
    """Minimal lock object for task mutation tests."""

    def __init__(self) -> None:
        """Initialize the fake lock."""
        self.enter_calls: int = 0
        self.exit_calls: int = 0

    def __enter__(self) -> bool:
        """Record context manager entry."""
        self.enter_calls += 1
        return True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Record context manager exit."""
        self.exit_calls += 1

def test_dummy_lock_context_manager() -> None:
    """Enter and exit without synchronizing anything."""
    lock = DummyLock()

    with lock as result:
        assert result is True


def test_download_status_repr() -> None:
    """Return a stable enum representation."""
    assert repr(DownloadStatus.PENDING) == "DownloadStatus.PENDING"


def test_download_task_initializes_defaults() -> None:
    """Initialize task state from required values and defaults."""
    task = DownloadTask("https://example.com/file.zip", "downloads/file.zip")

    assert task.url == "https://example.com/file.zip"
    assert task.dest == Path("downloads/file.zip")
    assert task.headers == dict(DEFAULT_HEADERS)
    assert task.kind == "file"
    assert task.progress_name == "file.zip"
    assert task.downloaded == 0
    assert task.total == -1
    assert task.status is DownloadStatus.PENDING
    assert task.is_canceled is False


def test_download_task_initializes_custom_values(tmp_path: Path) -> None:
    """Initialize task state from provided optional values."""
    dest = tmp_path / "target.bin"
    headers = {"Authorization": "Bearer token"}

    task = DownloadTask(
        "https://example.com/file.zip",
        dest,
        headers=headers,
        kind="folder",
        progress_name="custom name",
    )

    assert task.dest == dest
    assert task.headers == headers
    assert task.kind == "folder"
    assert task.progress_name == "custom name"


def test_download_task_initializes_binary_io_dest(tmp_path: Path) -> None:
    """Initialize task state from a binary file-like destination."""
    path = tmp_path / "target.bin"
    with path.open("wb") as file_obj:
        task = DownloadTask("https://example.com/file.zip", file_obj)

        assert task.dest is file_obj


def test_download_task_progress_name_uses_url_for_binary_io(
    tmp_path: Path,
) -> None:
    """Use the URL as progress name for binary file-like destinations."""
    path = tmp_path / "target.bin"
    with path.open("wb") as file_obj:
        task = DownloadTask("https://example.com/file.zip", file_obj)

        assert task.progress_name == "https://example.com/file.zip"


def test_download_task_headers_are_copied() -> None:
    """Copy provided headers so later mutations do not affect the task."""
    headers = {"User-Agent": "custom"}
    task = DownloadTask(
        "https://example.com/file.zip",
        "file.zip",
        headers=headers,
    )

    headers["User-Agent"] = "changed"

    assert task.headers == {"User-Agent": "custom"}


def test_download_task_ids_are_unique() -> None:
    """Assign unique IDs to new tasks."""
    first = DownloadTask("https://example.com/first.zip", "first.zip")
    second = DownloadTask("https://example.com/second.zip", "second.zip")

    assert second.id != first.id


def test_download_task_setters_use_lock() -> None:
    """Mutate task progress and status through the configured lock."""
    task = DownloadTask("https://example.com/file.zip", "file.zip")
    lock = FakeLock()
    task.set_lock(lock)

    task.downloaded = 10
    task.total = 20
    task.status = DownloadStatus.RUNNING

    assert task.downloaded == 10
    assert task.total == 20
    assert task.status is DownloadStatus.RUNNING
    assert lock.enter_calls == 3
    assert lock.exit_calls == 3


def test_download_task_cancel_sets_event_and_status() -> None:
    """Mark the task as canceled and set the cancel event."""
    task = DownloadTask("https://example.com/file.zip", "file.zip")
    event = FakeEvent()
    task.set_cancel_event(event)

    task.cancel()

    assert task.is_canceled is True
    assert task.status is DownloadStatus.CANCELED
    assert event.set_calls == 1


def test_download_task_rejects_invalid_url() -> None:
    """Reject invalid URLs during task creation."""
    with pytest.raises(ValueError):
        DownloadTask("not-a-url", "file.zip")


def test_download_task_rejects_invalid_url_type() -> None:
    """Reject non-string URLs during task creation."""
    with pytest.raises(TypeError):
        DownloadTask(
            123,  # pyright: ignore[reportArgumentType]
            "file.zip",
        )


def test_download_task_rejects_invalid_dest() -> None:
    """Reject invalid destinations during task creation."""
    with pytest.raises(TypeError):
        DownloadTask(
            "https://example.com/file.zip",
            123,  # pyright: ignore[reportArgumentType]
        )
