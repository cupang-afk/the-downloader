import io
import unittest
from pathlib import Path
from typing import Any, cast

from src.the_downloader.task import DownloadStatus, DownloadTask


class DownloadTaskConstructorTests(unittest.TestCase):
    def test_task_accepts_url_destination_headers_kind_and_progress_name(self) -> None:
        task = DownloadTask(
            "https://example.com/file.bin",
            "file.bin",
            headers={"Accept": "application/octet-stream"},
            kind="file",
            progress_name="example file",
        )

        self.assertEqual(task.url, "https://example.com/file.bin")
        self.assertEqual(task.dest, Path("file.bin"))
        self.assertEqual(task.headers, {"Accept": "application/octet-stream"})
        self.assertEqual(task.kind, "file")
        self.assertEqual(task.progress_name, "example file")
        self.assertEqual(task.status, DownloadStatus.PENDING)
        self.assertEqual(task.total, -1)
        self.assertEqual(task.downloaded, 0)
        self.assertFalse(task.is_canceled)

    def test_task_uses_path_name_as_default_progress_name(self) -> None:
        task = DownloadTask("https://example.com/file.bin", "folder/file.bin")

        self.assertEqual(task.progress_name, "file.bin")

    def test_task_uses_url_as_progress_name_for_binary_destination(self) -> None:
        destination = io.BytesIO()
        task = DownloadTask("https://example.com/file.bin", destination)

        self.assertEqual(task.dest, destination)
        self.assertEqual(task.progress_name, "https://example.com/file.bin")

    def test_task_cancel_sets_cancel_event_and_status(self) -> None:
        task = DownloadTask("https://example.com/file.bin", "file.bin")

        task.cancel()

        self.assertTrue(task.is_canceled)
        self.assertEqual(task.status, DownloadStatus.CANCELED)

    def test_task_rejects_invalid_url_type(self) -> None:
        with self.assertRaises(TypeError):
            DownloadTask(cast(Any, 123), "file.bin")

    def test_task_rejects_url_without_scheme_or_netloc(self) -> None:
        with self.assertRaises(ValueError):
            DownloadTask("not-a-url", "file.bin")

    def test_task_rejects_invalid_destination_type(self) -> None:
        with self.assertRaises(TypeError):
            DownloadTask("https://example.com/file.bin", cast(Any, object()))


if __name__ == "__main__":
    unittest.main()
