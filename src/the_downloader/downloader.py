import queue
import shutil
import tempfile
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock, current_thread, main_thread
from typing import BinaryIO, Self

from .callback import DownloadCallback, handle_callback
from .constants import CHUNK_SIZE, TMP_FILE_PREFIX
from .http_session import get_session
from .provider.base import DownloadProvider
from .task import DownloadTask, DownloadTaskID, DownloadTaskStatus
from .types import ExcInfo, Overwrite
from .utils.file_utils import rename_path, resolve_path, safe_delete
from .utils.metadata_utils import get_total_size


class Downloader:
    """Implement a main downloader class for single-file downloads.

    Provides core functionality for downloading files with progress tracking,
    error handling, and cancellation support using a provider implementation.
    """

    def __init__(
        self, download_callback: DownloadCallback, downloader: DownloadProvider
    ) -> None:
        """Initialize the downloader with callback and provider.

        Args:
            download_callback: Handler for download progress and events
            downloader: Provider implementation for actual downloads
        """
        self.callback = download_callback
        self.downloader = downloader
        self._running_event: Event = Event()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    def start(self) -> None:
        """Start the downloader.

        Raises:
            RuntimeError: If the downloader is already running
        """
        if self.is_running:
            raise RuntimeError("Downloader is already running")

        self._running_event.set()
        self.downloader.__pre_start__()

    def stop(self) -> None:
        """Stop the downloader.

        Raises:
            RuntimeError: If the downloader is not running
        """
        if not self.is_running:
            raise RuntimeError("Downloader is not running")

        self._running_event.clear()
        self.downloader.__post_stop__()

    def download(
        self, task: DownloadTask | list[DownloadTask], overwrite: bool = False
    ) -> None:
        """Download one or more files.

        Args:
            task: Single download task or list of download tasks
            overwrite: Whether to overwrite existing files

        Raises:
            RuntimeError: If the downloader is not running
        """
        if not self.is_running:
            raise RuntimeError("Downloader is not running")

        task = task if isinstance(task, list) else [task]

        for t in task:
            self._execute_download(t, overwrite)

    def _on_start(self, task: DownloadTask) -> None:
        task.status = DownloadTaskStatus.RUNNING
        handle_callback(self.callback.on_start, task)

    def _on_complete(self, task: DownloadTask) -> None:
        task.status = DownloadTaskStatus.COMPLETED
        handle_callback(self.callback.on_complete, task)

    def _on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None:
        task.status = DownloadTaskStatus.ERROR
        handle_callback(self.callback.on_error, task, exc_info)

    def _on_cancel(self, task: DownloadTask) -> None:
        task.status = DownloadTaskStatus.CANCELED
        handle_callback(self.callback.on_cancel, task)

    def _resolve_dest_path(self, dest: Path, overwrite: bool) -> Path:
        dest = resolve_path(dest)

        if dest.exists() and not overwrite:
            dest = rename_path(dest)

        dest.parent.mkdir(parents=True, exist_ok=True)

        return dest

    def _finalize_download(self, tmp_path: Path, dest: BinaryIO | Path) -> None:
        if isinstance(dest, Path):
            safe_delete(dest.absolute())
            shutil.move(tmp_path, dest.absolute())
            return

        with tmp_path.open("rb") as f:
            shutil.copyfileobj(f, dest, CHUNK_SIZE)

    def _prepare_destination(self, task: DownloadTask, overwrite: bool) -> None:
        if not isinstance(task.dest, Path):
            return

        orig_name = task.dest.name
        task.dest = self._resolve_dest_path(task.dest, overwrite)

        if orig_name.lower() == task.progress_name.lower():
            task.progress_name = task._validate_progress_name(None)

    def _create_temp_destination(self, task: DownloadTask) -> Path:
        parent_dir = task.dest.parent if isinstance(task.dest, Path) else None

        if task.is_file:
            with tempfile.NamedTemporaryFile(
                prefix=TMP_FILE_PREFIX,
                dir=parent_dir,
                delete=False,
            ) as f:
                return Path(f.name)
        else:
            with tempfile.TemporaryDirectory(
                prefix=TMP_FILE_PREFIX,
                dir=parent_dir,
                delete=False,
            ) as d:
                return Path(d)

    def _execute_download(self, task: DownloadTask, overwrite: bool) -> None:
        if not self.is_running:
            raise RuntimeError("Downloader is not running")

        if task.is_canceled:
            self._on_cancel(task)
            return

        temp_path: Path | None = None

        try:
            if task.is_file:
                with get_session() as session:
                    task.total = get_total_size(session, task.url, task.headers)

            self._prepare_destination(task, overwrite)
            temp_path = self._create_temp_destination(task)

            self._on_start(task)
            self.downloader.download(task, temp_path, self.callback.on_progress)

            if task.is_canceled:
                self._on_cancel(task)
                return

            self._finalize_download(temp_path, task.dest)
            self._on_complete(task)

        except KeyboardInterrupt:
            if current_thread() is main_thread():
                self._on_cancel(task)
                task.cancel()
            raise

        except Exception as e:
            self._on_error(task, (type(e), e, e.__traceback__))

        finally:
            if temp_path is not None:
                safe_delete(temp_path)

    @property
    def is_running(self) -> bool:
        """Check if the downloader is currently running.

        Returns:
            True if the downloader is running, False otherwise
        """
        return self._running_event.is_set()


class QueueDownloader(Downloader):
    """Implement a concurrent downloader class for handling multiple downloads.

    Extends basic Downloader to support concurrent downloads using a thread
    pool. Manages a queue of download tasks and processes them using multiple
    worker threads for improved performance.
    """

    def __init__(
        self,
        download_callback,
        downloader,
        workers: int = 4,
    ) -> None:
        """Initialize the queue downloader with worker configuration.

        Args:
            download_callback: Handler for download progress and events
            downloader: Provider implementation for actual downloads
            workers: Number of worker threads to use for concurrent downloads
        """
        super().__init__(download_callback, downloader)

        self.worker_count = workers

        self.executor: ThreadPoolExecutor | None = None
        self.workers: list[Future] = []

        self.download_task: queue.Queue[tuple[DownloadTask, Overwrite]] = queue.Queue()

        self.results: dict[DownloadTaskID, DownloadTask] = {}
        self.result_lock: Lock = Lock()

        self.task_lock: Lock = Lock()
        self.submitted_task: set[DownloadTask] = set()

        self._stop_event: Event = Event()
        self._finish_event: Event = Event()

    def start(self) -> None:
        """Start the queue downloader with worker threads.

        Raises:
            RuntimeError: If the queue downloader is already running
        """
        if self.is_running:
            raise RuntimeError("QueueDownloader already running")

        super().start()

        self.results.clear()
        self._finish_event.clear()
        self._stop_event.clear()
        self.executor = ThreadPoolExecutor(max_workers=self.worker_count)
        self.workers.clear()
        for _ in range(self.worker_count):
            self.workers.append(self.executor.submit(self._worker))

    def stop(self) -> None:
        """Stop the queue downloader and wait for all tasks to complete.

        Raises:
            RuntimeError: If the queue downloader is not running
        """
        if not self.is_running:
            raise RuntimeError("QueueDownloader not running")

        # cancel tasks first
        self.cancel()

        # wait until queue is fully processed
        self._stop_event.set()
        self.download_task.join()

        if self.executor:
            self.executor.shutdown(wait=True)

        self.workers.clear()

        super().stop()

    def add_task(self, task: DownloadTask, overwrite: bool = False) -> None:
        """Add a single download task to the queue.

        Args:
            task: The download task to add
            overwrite: Whether to overwrite existing files

        Raises:
            RuntimeError: If the downloader is stopping
        """
        if self._stop_event.is_set():
            raise RuntimeError("Downloader stopping")
        if self._finish_event.is_set():
            raise RuntimeError("Cannot add task after completion has been signaled.")
        with self.task_lock:
            self.submitted_task.add(task)
        self.download_task.put((task, overwrite))

    def add_tasks(self, tasks: list[DownloadTask], overwrite: bool = False) -> None:
        """Add multiple download tasks to the queue.

        Args:
            tasks: List of download tasks to add
            overwrite: Whether to overwrite existing files

        Raises:
            RuntimeError: If the downloader is stopping
        """
        if self._stop_event.is_set():
            raise RuntimeError("Downloader stopping")
        if self._finish_event.is_set():
            raise RuntimeError("Cannot add task after completion has been signaled.")
        with self.task_lock:
            for task in tasks:
                self.submitted_task.add(task)
        for task in tasks:
            self.download_task.put((task, overwrite))

    def finish(self) -> None:
        """Mark the downloader as complete and signal workers to stop.

        After this is called, no new tasks should be added. Sentinel values
        (None) are queued so each worker exits after processing all
        remaining tasks.
        """
        if self._finish_event.is_set():
            return
        # Sentinel to signal worker threads to exit
        for _ in range(self.worker_count):
            self.download_task.put(None)  # type: ignore
        self._finish_event.set()

    def cancel(self) -> None:
        """Cancel all pending download tasks and signal workers to exit."""
        with self.task_lock:
            tasks = list(self.submitted_task)

        for task in tasks:
            task.cancel()

        self.finish()

    def store_result(self, task: DownloadTask) -> None:
        """Store the result of a completed download task.

        Args:
            task: The completed download task to store
        """
        with self.result_lock:
            self.results[task.id] = task

    def get_result(self, task: DownloadTask) -> DownloadTask | None:
        """Get the result of a specific download task.

        Args:
            task: The download task to retrieve the result for

        Returns:
            The completed download task or None if not found
        """
        with self.result_lock:
            return self.results.get(task.id)

    def get_all_results(self) -> dict[DownloadTaskID, DownloadTask]:
        """Get all completed download task results.

        Returns:
            Dictionary mapping task IDs to completed download tasks

        Note:
            This method will block until all tasks have completed.
        """
        if self.is_running:
            self.download_task.join()

        with self.result_lock:
            return self.results.copy()

    def _worker(self) -> None:
        while True:
            task = None
            try:
                item = self.download_task.get(timeout=0.1)
                if item is None:
                    self.download_task.task_done()
                    break
                task, overwrite = item
                self._execute_download(task, overwrite)
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                pass  # handled by _execute_download
            finally:
                if task is not None:
                    self.store_result(task)
                    self.download_task.task_done()
                    with self.task_lock:
                        self.submitted_task.discard(task)

    @property
    def is_finished(self) -> bool:  # noqa: D102
        return self.download_task.empty()
