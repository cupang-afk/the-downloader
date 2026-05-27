import unittest
from pathlib import PurePath
from typing import Any, cast, override

from src.the_downloader.callback import BaseCallback
from src.the_downloader.manager import BasicDownloadManager
from src.the_downloader.provider import BaseProvider
from src.the_downloader.task import DownloadTask
from src.the_downloader.types.alias import ExcInfo
from src.the_downloader.types.protocol import CheckCanceled, UpdateProgress


class ExampleProvider(BaseProvider):
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


class ExampleCallback(BaseCallback):
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


class ManagerConstructorTests(unittest.TestCase):
    def test_manager_accepts_retry_settings_as_keyword_args(self) -> None:
        manager = BasicDownloadManager(
            provider=ExampleProvider(),
            callback=ExampleCallback(),
            max_retries=1,
            retry_delay=0,
            retry_backoff_factor=1,
        )

        self.assertEqual(manager.max_retries, 1)
        self.assertEqual(manager.retry_delay, 0)
        self.assertEqual(manager.retry_backoff_factor, 1)

    def test_manager_rejects_invalid_provider(self) -> None:
        with self.assertRaises(TypeError):
            BasicDownloadManager(
                provider=cast(Any, object()),
                callback=ExampleCallback(),
            )

    def test_manager_rejects_invalid_callback(self) -> None:
        with self.assertRaises(TypeError):
            BasicDownloadManager(
                provider=ExampleProvider(),
                callback=cast(Any, object()),
            )


if __name__ == "__main__":
    unittest.main()
