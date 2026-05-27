import unittest
from pathlib import PurePath
from typing import override

from src.the_downloader.callback import BaseCallback
from src.the_downloader.manager import BasicDownloadManager
from src.the_downloader.provider import BaseProvider
from src.the_downloader.task import DownloadTask
from src.the_downloader.types.alias import ExcInfo
from src.the_downloader.types.protocol import CheckCanceled, UpdateProgress


class InternalProvider(BaseProvider):
    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        return None


class InternalCallback(BaseCallback):
    @override
    def on_start(self, task: DownloadTask) -> None:
        return None

    @override
    def on_finish(self, task: DownloadTask) -> None:
        return None

    @override
    def on_cancel(self, task: DownloadTask) -> None:
        return None

    @override
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None:
        return None

    @override
    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **optional_data: object,
    ) -> None:
        return None


class ManagerInternalTests(unittest.TestCase):
    def test_basic_manager_initializes_empty_queue_and_cleared_running_event(
        self,
    ) -> None:
        manager = BasicDownloadManager(InternalProvider(), InternalCallback())

        self.assertEqual(len(manager._simple_queue), 0)  # pyright: ignore[reportPrivateUsage]
        self.assertFalse(manager._running.is_set())  # pyright: ignore[reportPrivateUsage]

    def test_add_appends_task_to_internal_queue(self) -> None:
        manager = BasicDownloadManager(InternalProvider(), InternalCallback())
        task = DownloadTask("https://example.com/file.bin", "file.bin")

        manager.start()
        manager.add(task)

        self.assertEqual(list(manager._simple_queue), [task])  # pyright: ignore[reportPrivateUsage]


if __name__ == "__main__":
    unittest.main()
