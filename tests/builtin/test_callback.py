"""Tests for builtin download callback implementations."""

from pathlib import Path

import pytest

from the_downloader.callback import BasicDownloadCallback, NullDownloadCallback
from the_downloader.task import DownloadTask
from the_downloader.types.alias import ExcInfo


def test_basic_download_callback_on_start(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print a start message for the task."""
    callback = BasicDownloadCallback()
    task = DownloadTask(
        "https://example.com/file.zip",
        Path("file.zip"),
        progress_name="file",
    )

    callback.on_start(task)

    assert capsys.readouterr().out == "Download Status of file: started\n"


def test_basic_download_callback_on_cancel(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print a cancellation message for the task."""
    callback = BasicDownloadCallback()
    task = DownloadTask(
        "https://example.com/file.zip",
        Path("file.zip"),
        progress_name="file",
    )

    callback.on_cancel(task)

    assert capsys.readouterr().out == "Download Status of file: canceled\n"


def test_basic_download_callback_on_finish(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print a finish message for the task."""
    callback = BasicDownloadCallback()
    task = DownloadTask(
        "https://example.com/file.zip",
        Path("file.zip"),
        progress_name="file",
    )

    callback.on_finish(task)

    assert capsys.readouterr().out == "Download Status of file: finished\n"


def test_basic_download_callback_on_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print an error message with exception info."""
    callback = BasicDownloadCallback()
    task = DownloadTask(
        "https://example.com/file.zip",
        Path("file.zip"),
        progress_name="file",
    )
    error = RuntimeError("boom")
    exc_info: ExcInfo = (RuntimeError, error, error.__traceback__)

    callback.on_error(task, exc_info)

    assert capsys.readouterr().out == (
        "Download Status of file: error: "
        f"{(RuntimeError, error, error.__traceback__)}\n"
    )


def test_basic_download_callback_on_progress_with_total(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print percent progress when total bytes are known."""
    callback = BasicDownloadCallback()
    task = DownloadTask(
        "https://example.com/file.zip",
        Path("file.zip"),
        progress_name="file",
    )

    callback.on_progress(task, 5, 10)

    assert capsys.readouterr().out == (
        "Download Status of file: progress 50.00% (5/10 bytes)\n"
    )


def test_basic_download_callback_on_progress_without_total(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print byte progress when total bytes are unknown."""
    callback = BasicDownloadCallback()
    task = DownloadTask(
        "https://example.com/file.zip",
        Path("file.zip"),
        progress_name="file",
    )

    callback.on_progress(task, 5, -1)

    assert capsys.readouterr().out == (
        "Download Status of file: progress 5 bytes\n"
    )


def test_null_download_callback_ignores_all_events(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ignore all callback events without output or errors."""
    callback = NullDownloadCallback()
    task = DownloadTask(
        "https://example.com/file.zip",
        Path("file.zip"),
        progress_name="file",
    )
    error = RuntimeError("boom")
    exc_info: ExcInfo = (RuntimeError, error, error.__traceback__)

    callback.on_start(task)
    callback.on_progress(task, 5, 10, provider="fake")
    callback.on_finish(task)
    callback.on_cancel(task)
    callback.on_error(task, exc_info)

    assert capsys.readouterr().out == ""
