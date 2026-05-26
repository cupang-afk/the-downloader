import tempfile
import unittest
from pathlib import Path, PurePath
from typing import override

from src.the_downloader.callback import BaseCallback
from src.the_downloader.manager import BasicDownloadManager
from src.the_downloader.provider import BaseProvider
from src.the_downloader.task import DownloadStatus, DownloadTask
from src.the_downloader.types.alias import ExcInfo
from src.the_downloader.types.protocol import CheckCanceled, UpdateProgress


class RecordingCallback(BaseCallback):
    def __init__(self) -> None:
        self.events: list[str] = []
        self.errors: list[ExcInfo] = []

    @override
    def on_start(self, task: DownloadTask) -> None:
        self.events.append("start")

    @override
    def on_finish(self, task: DownloadTask) -> None:
        self.events.append("finish")

    @override
    def on_cancel(self, task: DownloadTask) -> None:
        self.events.append("cancel")

    @override
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None:
        self.events.append("error")
        self.errors.append(exc_info)

    @override
    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **optional_data: object,
    ) -> None:
        self.events.append("progress")


class FailsOnceProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__()
        self.attempts: int = 0

    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("temporary failure")
        Path(dest).write_bytes(b"downloaded")
        update_progress(10, 10)


class ManagerRetryFlowTests(unittest.TestCase):
    def test_manager_finishes_when_retry_eventually_succeeds(self) -> None:
        provider = FailsOnceProvider()
        callback = RecordingCallback()
        manager = BasicDownloadManager(
            provider=provider,
            callback=callback,
            max_retries=1,
            retry_delay=0,
            retry_backoff_factor=1,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            destination = Path(tmp_dir, "file.bin")
            task = DownloadTask("https://example.com/file.bin", destination)

            with manager:
                manager.add(task)
                manager.wait()

            self.assertEqual(provider.attempts, 2)
            self.assertEqual(task.status, DownloadStatus.FINISHED)
            self.assertEqual(destination.read_bytes(), b"downloaded")
            self.assertEqual(callback.events, ["start", "progress", "finish"])
            self.assertEqual(callback.errors, [])


if __name__ == "__main__":
    unittest.main()
