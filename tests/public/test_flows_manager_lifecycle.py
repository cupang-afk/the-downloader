import unittest
from pathlib import PurePath
from typing import override

from src.the_downloader.callback import BaseCallback
from src.the_downloader.manager import BasicDownloadManager
from src.the_downloader.provider import BaseProvider
from src.the_downloader.task import DownloadStatus, DownloadTask
from src.the_downloader.types.alias import ExcInfo
from src.the_downloader.types.protocol import CheckCanceled, UpdateProgress


class LifecycleProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__()
        self.pre_hook_calls: int = 0
        self.post_hook_calls: int = 0

    @override
    def __pre_hook__(self) -> None:
        self.pre_hook_calls += 1

    @override
    def __post_hook__(self) -> None:
        self.post_hook_calls += 1

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


class LifecycleCallback(BaseCallback):
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


class ManagerLifecycleFlowTests(unittest.TestCase):
    def test_start_and_stop_guard_running_state(self) -> None:
        manager = BasicDownloadManager(LifecycleProvider(), LifecycleCallback())

        manager.start()
        with self.assertRaises(RuntimeError):
            manager.start()

        manager.stop()
        with self.assertRaises(RuntimeError):
            manager.stop()

    def test_add_wait_and_cancel_require_running_manager(self) -> None:
        manager = BasicDownloadManager(LifecycleProvider(), LifecycleCallback())
        task = DownloadTask("https://example.com/file.bin", "file.bin")

        with self.assertRaises(RuntimeError):
            manager.add(task)
        with self.assertRaises(RuntimeError):
            manager.wait()
        with self.assertRaises(RuntimeError):
            manager.cancel()

    def test_context_manager_calls_provider_hooks_and_allows_add(self) -> None:
        provider = LifecycleProvider()
        manager = BasicDownloadManager(provider, LifecycleCallback())
        task = DownloadTask("https://example.com/file.bin", "file.bin")

        with manager:
            manager.add(task)
            manager.cancel()

        self.assertEqual(provider.pre_hook_calls, 1)
        self.assertEqual(provider.post_hook_calls, 1)
        self.assertEqual(task.status, DownloadStatus.CANCELED)

    def test_cancel_task_cancels_pending_or_running_task_only(self) -> None:
        manager = BasicDownloadManager(LifecycleProvider(), LifecycleCallback())
        pending = DownloadTask("https://example.com/pending.bin", "pending.bin")
        finished = DownloadTask("https://example.com/finished.bin", "finished.bin")
        finished.status = DownloadStatus.FINISHED

        manager.cancel_task(pending)
        manager.cancel_task(finished)

        self.assertEqual(pending.status, DownloadStatus.CANCELED)
        self.assertEqual(finished.status, DownloadStatus.FINISHED)


if __name__ == "__main__":
    unittest.main()
