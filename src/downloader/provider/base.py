"""Base classes for download providers."""

import os
import shutil
import signal
import subprocess
import threading
from abc import ABCMeta, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from logging import Logger
from pathlib import Path
from typing import Any, final

from ..callback import (
    CallbackNonZeroReturnError,
    ProgressCallback,
    ProgressDownloaded,
    ProgressTotal,
)
from ..logger import logger
from ..task import DownloadTask
from ..utils import ensure_path

CANCEL_EVENT = threading.Event()
CHUNK_SIZE = 8192  # 8KB


class DownloadProvider(metaclass=ABCMeta):
    """Abstract base class for download providers.

    Attributes:
        cancel_event: Threading event used to signal download cancellation.
        chunk_size: Size of chunks for reading/writing data in bytes.
    """

    def __init__(
        self,
        cancel_event: threading.Event = CANCEL_EVENT,
        chunk_size: int = CHUNK_SIZE,
    ):
        """Initializes the download provider.

        Args:
            cancel_event: Threading event used to signal download cancellation.
            chunk_size: Size of chunks for reading/writing data. Defaults to 8KB.
        """
        self.cancel_event = cancel_event
        self.chunk_size = chunk_size

    @final
    @property
    def logger(self) -> Logger:
        """The logger instance for this module."""
        return logger

    @final
    @property
    def is_canceled(self) -> bool:
        """Checks if the download has been canceled."""
        return self.cancel_event.is_set()

    @final
    def _handle_progress(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback,
        downloaded: ProgressDownloaded = 0,
        total: ProgressTotal = 0,
        **extra: Any,
    ) -> None:
        """Handles progress reporting via callback.

        Args:
            task: The download task being processed.
            progress_callback: Callback function to report progress.
            downloaded: Number of bytes downloaded so far. Defaults to 0.
            total: Total number of bytes to download. Defaults to 0.
            **extra: Additional keyword arguments passed to the callback.

        Raises:
            CallbackNonZeroReturnError: If the callback returns a non-None value.
        """
        if not callable(progress_callback):
            return
        if progress_callback(task, downloaded, total, **extra) is not None:
            raise CallbackNonZeroReturnError()

    def __pre_download__(self) -> None: ...

    def __post_download__(self) -> None: ...

    @abstractmethod
    def download(self, task: DownloadTask, progress_callback: ProgressCallback) -> None:
        """Downloads the specified task.

        Args:
            task: The download task to process.
            progress_callback: Callback function to report download progress.

        Note:
            task.dest is always passed as a Path object because the internal
            handler saves to a temporary file.
        """
        ...


class DownloadSubprocessProvider(DownloadProvider):
    """Abstract base class for subprocess-based download providers."""

    @final
    def ensure_binary(self, binary_path: str | Path) -> Path:
        """Ensures a binary executable exists and returns its absolute path.

        Args:
            binary_path: Path to the binary executable. Can be absolute or
                relative (in which case PATH is searched).

        Returns:
            The absolute Path to the binary executable.

        Raises:
            FileNotFoundError: If the binary does not exist or is not executable.
        """
        binary_path = ensure_path(binary_path)
        if binary_path.is_absolute():
            if not binary_path.is_file():
                raise FileNotFoundError(str(binary_path))
            return binary_path.absolute()
        else:
            bin_from_path = shutil.which(binary_path.name)
            if not bin_from_path:
                raise FileNotFoundError(binary_path.name)
            return Path(bin_from_path).absolute()

    @contextmanager
    def popen_wrapper(
        self, command: list[str], *, raise_nonzero_return=False, **popen_kwargs
    ) -> Iterator[subprocess.Popen]:
        """Context manager for subprocess execution.

        Args:
            command: Command and arguments to execute.
            raise_nonzero_return: Whether to raise an exception on non-zero
                return code. Defaults to False.
            **popen_kwargs: Additional keyword arguments passed to subprocess.Popen.

        Yields:
            subprocess.Popen: The subprocess instance.
        """
        if "stdout" not in popen_kwargs:
            popen_kwargs["stdout"] = subprocess.PIPE
        if "stderr" not in popen_kwargs:
            popen_kwargs["stderr"] = subprocess.PIPE
        if "stdin" not in popen_kwargs:
            popen_kwargs["stdin"] = subprocess.PIPE

        process = subprocess.Popen(command, **popen_kwargs)
        try:
            yield process
        finally:
            self.popen_terminate(process, raise_nonzero_return)

    def popen_terminate(self, process: subprocess.Popen, raise_nonzero_return=True):
        """Terminates a subprocess and handles its exit.

        Args:
            process: The subprocess to terminate.
            raise_nonzero_return: Whether to raise an exception on non-zero
                return code. Defaults to True.

        Raises:
            subprocess.CalledProcessError: If the process exits with a non-zero
                return code and raise_nonzero_return is True.
        """
        stdout = None
        stderr = None
        while process.poll() is None:
            try:
                stdout, stderr = process.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                    process.send_signal(signal.CTRL_C_EVENT)
                process.kill()
        if process.returncode != 0 and raise_nonzero_return:
            raise subprocess.CalledProcessError(
                returncode=process.returncode,
                cmd=process.args,
                output=stdout,
                stderr=stderr,
            )
