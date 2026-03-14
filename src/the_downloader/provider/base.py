import os
import shutil
import signal
import subprocess
from abc import ABCMeta, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from logging import Logger
from os import PathLike
from pathlib import Path
from typing import Any, final

from ..callback import handle_callback
from ..constants import CHUNK_SIZE
from ..logger import logger
from ..task import DownloadTask
from ..types import (
    ProgressCallback,
    ProgressDownloaded,
    ProgressTotal,
)
from ..utils.file_utils import resolve_path


class DownloadProvider(metaclass=ABCMeta):
    """Define an abstract base class for download providers.

    Defines the interface for different download provider implementations
    (e.g., requests, aria2, curl, wget) that handle the actual downloading
    of files using different underlying technologies.
    """

    def __init__(self, chunk_size: int = CHUNK_SIZE) -> None:
        """Initialize the download provider.

        Args:
            chunk_size: Size of chunks to use for downloading data
        """
        self._logger = logger.getChild(self.__class__.__name__)
        self._logger.debug("Initializing %s", self.__class__.__name__)
        self.chunk_size = chunk_size

    def __pre_start__(self) -> None:
        """Perform actions before the provider starts.

        This hook is called before the downloader enters its running state.
        Subclasses may override this to initialize resources, start external
        processes, or perform other setup operations.
        """
        return

    def __post_stop__(self) -> None:
        """Perform actions after the provider stops.

        This hook is called after the downloader exits its running state.
        Subclasses may override this to release resources, terminate external
        processes, or perform other cleanup operations.
        """
        return

    @final
    def _handle_progress_callback(
        self,
        callback: ProgressCallback,
        task: DownloadTask,
        downloaded: ProgressDownloaded,
        total: ProgressTotal,
        **extra: Any,
    ) -> None:
        task.downloaded = downloaded
        task.total = total
        handle_callback(callback, task, downloaded, total, **extra)

    @final
    @property
    def logger(self) -> Logger:
        """Get the logger instance for this provider.

        Returns:
            Logger instance for this provider class
        """
        return self._logger

    @abstractmethod
    def download(
        self,
        task: DownloadTask,
        dest: Path,
        progress_callback: ProgressCallback,
    ) -> None:
        """Download a file using this provider.

        Args:
            task: The download task containing URL and metadata
            dest: Destination path for the downloaded file
            progress_callback: Callback function for progress updates
        """
        ...


class SubprocessDownloaderMixin:
    """Provide a mixin class for subprocess-based download providers.

    Provides common functionality for download providers that use subprocess
    calls to external tools (e.g., aria2, curl, wget).
    """

    @final
    def resolve_binary(self, binary_path: str | PathLike[str] | Path) -> Path:
        """Resolve the path to a binary executable.

        Args:
            binary_path: Path to the binary (absolute or relative)

        Returns:
            Absolute path to the binary

        Raises:
            FileNotFoundError: If the binary cannot be found
        """
        binary_path = resolve_path(binary_path)
        if binary_path.is_absolute():
            if not binary_path.is_file():
                raise FileNotFoundError(str(binary_path))
            return binary_path.absolute()
        else:
            bin_from_path = shutil.which(binary_path.name)
            if not bin_from_path:
                raise FileNotFoundError(binary_path.name)
            return Path(bin_from_path).absolute()

    @final
    @contextmanager
    def popen_wrapper(
        self, command: list[str], *, raise_nonzero_return=False, **popen_kwargs
    ) -> Iterator[subprocess.Popen]:
        """Execute a subprocess with proper resource management.

        Args:
            command: Command to execute as a list of strings
            raise_nonzero_return: Whether to raise an exception on non-zero exit
            **popen_kwargs: Additional arguments for subprocess.Popen

        Yields:
            The subprocess.Popen instance

        Raises:
            subprocess.CalledProcessError: If raise_nonzero_return is True and
                the process exits with a non-zero code
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

    @final
    def popen_terminate(
        self,
        process: subprocess.Popen,
        raise_nonzero_return: bool = True,
        timeout: int = 15,
    ) -> None:
        """Terminate a subprocess and handle cleanup.

        Args:
            process: The subprocess to terminate
            raise_nonzero_return: Whether to raise an exception on non-zero exit
            timeout: Timeout in seconds for process communication

        Raises:
            subprocess.CalledProcessError: If raise_nonzero_return is True and
                the process exits with a non-zero code
        """
        stdout = None
        stderr = None
        while process.poll() is None:
            try:
                stdout, stderr = process.communicate(timeout=timeout)
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
