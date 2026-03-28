"""Git provider implementation for the downloader module.

This module provides a GitDownloader class that uses git to download repositories
with progress tracking and cancellation support.
"""

import os
import re
import stat
import subprocess
from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path
from types import MappingProxyType

from src.the_downloader import (
    DownloadProvider,
    DownloadTask,
    ProviderError,
    SubprocessDownloaderMixin,
)
from src.the_downloader.constants import CHUNK_SIZE
from src.the_downloader.types import ProgressCallback


class GitError(ProviderError):
    """Represent an error class for Git download provider exceptions."""

    pass


class GitDownloader(DownloadProvider, SubprocessDownloaderMixin):
    """Implement a GitDownloader that uses `git` to download repositories."""

    STATUS_MAP = MappingProxyType(
        {
            "enumerating objects": "Enumerating",
            "counting objects": "Counting",
            "compressing objects": "Compressing",
            "writing objects": "Writing",
            "receiving objects": "Receiving",
            "unpacking objects": "Unpacking",
            "resolving deltas": "Resolving",
            "checking connectivity": "Checking",
            "checking out files": "Checkout",
            "updating files": "Updating",
            "filtering content": "Filtering",
        }
    )

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        git_bin: str | Path | None = None,
    ) -> None:
        """Initialize the Git downloader.

        Args:
            chunk_size: Size of chunks to use for downloading data
            git_bin: Path to the git binary executable
        """
        super().__init__(chunk_size)
        self.bin = self.resolve_binary(
            git_bin or ("git" if os.name != "nt" else "git.exe")
        )
        self.cmd = [str(self.bin), "clone", "--progress"]

        # Matches progress counters like "(75/177)" in git clone output
        self.git_pattern = re.compile(r"\((\d+)/(\d+)\)")

    def _set_permission(self, dir: Path):
        """Set write permissions for a directory and its contents.

        Args:
            dir: Directory to set permissions for
        """
        if not dir.exists():
            return
        with suppress(OSError):
            dir.chmod(stat.S_IWRITE)
        for file in dir.rglob("*"):
            with suppress(OSError):
                file.chmod(stat.S_IWRITE)

    def _iter_process_output(
        self,
        process: subprocess.Popen,
        task: DownloadTask,
    ) -> Iterator[str]:
        """Iterate through process output lines.

        Args:
            process: The subprocess to read output from
            task: The download task being processed

        Yields:
            Output lines from the process
        """
        while True:
            if process.poll() is not None:
                break
            if task.is_canceled:
                break
            if not process.stdout:
                break
            line: str = process.stdout.readline()
            if not line:
                break
            line = line.strip()

            yield line

    def _detect_git_status(self, line: str) -> str:
        """Detect git status from output line.

        Args:
            line: Output line from git command

        Returns:
            Detected status string
        """
        for key, status in self.STATUS_MAP.items():
            if key in line:
                return status
        return "?"

    def _extract_git_speed(self, line: str) -> str:
        """Extract git download speed from output line.

        Args:
            line: Output line from git command

        Returns:
            Extracted speed string
        """
        if "|" in line:
            return line.split("|", 1)[-1].strip()
        return ""

    def download(
        self,
        task: DownloadTask,
        dest: Path,
        progress_callback: ProgressCallback,
    ) -> None:
        """Download a Git repository.

        Args:
            task: The download task containing URL and metadata
            dest: Destination path for the downloaded repository
            progress_callback: Callback function for progress updates

        Raises:
            GitError: If the download fails
        """
        with self.popen_wrapper(
            [*self.cmd, task.url, str(dest.absolute())],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=None,
            universal_newlines=True,
            bufsize=1,
        ) as p:
            try:
                for line in self._iter_process_output(p, task):
                    line_lower = line.lower()

                    if "done" in line_lower:
                        continue

                    matches = self.git_pattern.search(line)
                    if not matches:
                        continue

                    status = self._detect_git_status(line_lower)
                    speed = self._extract_git_speed(line)

                    total = int(matches.group(2))
                    downloaded = int(matches.group(1))
                    self._handle_progress_callback(
                        progress_callback,
                        task,
                        downloaded,
                        total,
                        git=True,
                        git_status=status,
                        git_speed=speed,
                    )
            except Exception as e:
                raise GitError(
                    f"Error downloading {task.url} for {task.dest.name}"
                ) from e
            finally:
                if not task.is_canceled:
                    self._set_permission(dest)
