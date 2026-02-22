"""Main downloader module with callback support."""

import tempfile
from pathlib import Path
from typing import IO, Callable

from .callback import DefaultDownloadCallback, DownloadCallback
from .logger import logger
from .provider.base import DownloadProvider, DownloadSubprocessProvider
from .task import DownloadTask
from .utils import ensure_path, rename_path, safe_delete


class DownloadError(Exception):
    """Exception raised when a download fails."""

    pass


class Downloader:
    """Main downloader class that orchestrates download operations.

    This class manages download tasks, handles callbacks for progress
    reporting, and provides cancellation support.

    Attributes:
        callback: The callback instance for download events.
        downloader: The download provider implementation.
    """

    def __init__(
        self,
        download_callback: DownloadCallback | None,
        downloader: DownloadProvider | DownloadSubprocessProvider,
    ):
        """Initializes the Downloader.

        Args:
            download_callback: Callback for download events. If None,
                DefaultDownloadCallback will be used.
            downloader: The download provider implementation.
        """
        self.callback = download_callback or DefaultDownloadCallback()
        self.downloader = downloader

    def cancel(self) -> None:
        """Signals the downloader to cancel the current download."""
        logger.info("Cancelling download")
        self.downloader.cancel_event.set()

    def reset_cancel(self) -> None:
        """Resets the cancel event, allowing new downloads to proceed."""
        logger.info("Resetting cancel event")
        self.downloader.cancel_event.clear()

    def _ensure_parent_dir_exists(self, dest: Path) -> None:
        """Ensures the parent directory of the destination exists.

        Args:
            dest: The destination path.
        """
        logger.debug(f"Ensure parent directory of {dest} exists")
        parent_path = dest.parent
        if not parent_path.exists():
            logger.debug(f"Parent directory of {dest} does not exist, creating...")
            parent_path.mkdir(parents=True, exist_ok=True)

    def _handle_dest(self, path: Path, overwrite: bool) -> Path:
        """Handles the destination path, renaming if necessary.

        Args:
            path: The destination path.
            overwrite: Whether to overwrite existing files.

        Returns:
            The resolved destination path.
        """
        logger.debug("Handle save path")
        if not isinstance(path, Path):
            return path

        path = ensure_path(path)

        if path.exists() and not overwrite:
            logger.debug(f"{path} is exists, but overwrite is False renaming")
            new_path = rename_path(path)
            logger.debug(f"Rename {path} to {new_path}")
            path = new_path
        self._ensure_parent_dir_exists(path)
        return path

    def _handle_callback(self, callback: Callable, *args, **kwargs) -> object | None:
        """Executes a callback function if it is callable.

        Args:
            callback: The callback function to execute.
            *args: Positional arguments for the callback.
            **kwargs: Keyword arguments for the callback.

        Returns:
            The result of the callback, or None if not callable.
        """
        logger.debug("Handle callback")
        if not callable(callback):
            logger.debug(f"Cannot handle callback because {callback} is not callable")
            return None
        logger.debug(f"Running callback: {callback} with args: ({*args, *kwargs})")
        return callback(*args, **kwargs)

    def _handle_result(self, result: Path | None, save_obj: IO[bytes] | Path) -> None:
        """Handles the download result by moving or writing data.

        Args:
            result: Path to the temporary result file, or None if cancelled.
            save_obj: The final destination (Path or file-like object).
        """
        if result is None:
            return

        logger.debug("Handle result")

        if isinstance(save_obj, Path):
            logger.debug(
                f"save_obj is path: {save_obj}, cleaning up and rename {result}"
            )
            safe_delete(save_obj.absolute())
            result.rename(save_obj.absolute())
        else:
            logger.debug(f"save_obj is writeable object: {save_obj}, writing")
            chunk_size = 8192
            with result.open("rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    save_obj.write(chunk)
        safe_delete(result)

    def _handle_download(self, task: DownloadTask, save_tmp: Path) -> Path | None:
        """Handles a single download task.

        Args:
            task: The download task to process.
            save_tmp: Path to the temporary file for downloading.

        Returns:
            Path to the downloaded file, or None if cancelled.

        Raises:
            DownloadError: If the download fails and no error callback is set.
        """
        tmp_task = task.copy(dest=save_tmp)

        try:
            self._handle_callback(self.callback.on_start, tmp_task)
            self.downloader.download(tmp_task, self.callback.on_progress)
            if self.downloader.is_canceled:
                self._handle_callback(self.callback.on_cancel, tmp_task)
                return None
            else:
                self._handle_callback(self.callback.on_complete, tmp_task)
                return save_tmp
        except BaseException as e:
            # Treat KeyboardInterrupt as cancel when is_canceled is False
            if isinstance(e, KeyboardInterrupt) and not self.downloader.is_canceled:
                self._handle_callback(self.callback.on_cancel, tmp_task)
                return None

            if callable(self.callback.on_error):
                self._handle_callback(
                    self.callback.on_error, tmp_task, (type(e), e, e.__traceback__)
                )
                return None
            else:
                raise DownloadError(
                    f"Something wrong while downloading {tmp_task.progress_name}"
                ) from e

    def download(
        self, task: DownloadTask | list[DownloadTask], overwrite: bool = False
    ) -> list[IO[bytes] | Path]:
        """Downloads one or more tasks.

        Args:
            task: A single task or list of tasks to download.
            overwrite: Whether to overwrite existing files. Defaults to False.

        Returns:
            List of destination paths or file objects.
        """
        if not isinstance(task, list):
            task = [task]

        download_result: list[IO[bytes] | Path] = []
        try:
            self.downloader.__pre_download__()
            for t in task:
                if isinstance(t.dest, Path):
                    dest = self._handle_dest(t.dest, overwrite)
                    progress_name = (
                        dest.name
                        if t.progress_name is not None
                        and t.progress_name.lower() == t.dest.name.lower()
                        else t.progress_name
                    )
                    t = t.copy(dest=dest, progress_name=progress_name)
                result = None
                with tempfile.NamedTemporaryFile(
                    prefix="dl_temp",
                    dir=t.dest.parent if isinstance(t.dest, Path) else None,
                    delete=False,
                ) as f:
                    save_tmp = Path(f.name)
                    try:
                        result = self._handle_download(t, save_tmp)
                        f.close()
                        self._handle_result(result, t.dest)
                    finally:
                        f.close()
                        safe_delete(save_tmp)
                download_result.append(t.dest)
        finally:
            self.downloader.__post_download__()

        return download_result
