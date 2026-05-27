import unittest

from src.the_downloader.task import DownloadStatus, DownloadTask, DummyLock


class DownloadTaskInternalTests(unittest.TestCase):
    def test_task_initializes_private_state(self) -> None:
        task = DownloadTask("https://example.com/file.bin", "file.bin")

        self.assertEqual(task._downloaded, 0)  # pyright: ignore[reportPrivateUsage]
        self.assertEqual(task._total, -1)  # pyright: ignore[reportPrivateUsage]
        self.assertEqual(task._status, DownloadStatus.PENDING)  # pyright: ignore[reportPrivateUsage]
        self.assertIsInstance(task._lock, DummyLock)  # pyright: ignore[reportPrivateUsage]

    def test_task_setters_update_private_state(self) -> None:
        task = DownloadTask("https://example.com/file.bin", "file.bin")

        task.downloaded = 10
        task.total = 100
        task.status = DownloadStatus.RUNNING

        self.assertEqual(task._downloaded, 10)  # pyright: ignore[reportPrivateUsage]
        self.assertEqual(task._total, 100)  # pyright: ignore[reportPrivateUsage]
        self.assertEqual(task._status, DownloadStatus.RUNNING)  # pyright: ignore[reportPrivateUsage]


if __name__ == "__main__":
    unittest.main()
