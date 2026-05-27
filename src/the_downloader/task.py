"""Download task and status definitions.

This module defines the DownloadTask class which represents a single download
operation, and the DownloadStatus enum which tracks its state.
"""

from collections.abc import Mapping
from contextlib import AbstractContextManager
from enum import Enum, auto
from itertools import count
from pathlib import Path
from threading import Event
from types import MappingProxyType, TracebackType
from typing import Literal, override
from urllib.parse import urlparse

from .__version__ import __version__
from .types.protocol import BinaryIOProtocol, EventProtocol

DEFAULT_HEADERS: MappingProxyType[str, str] = MappingProxyType(
    {"User-Agent": f"TheDownloader/{__version__}"}
)


def _validate_dest(value: str | Path | BinaryIOProtocol) -> Path | BinaryIOProtocol:
    """Validates and converts the destination path.

    Args:
        value: The destination as a string, Path, or BinaryIOProtocol.

    Returns:
        The validated destination as a Path or BinaryIOProtocol.

    Raises:
        TypeError: If the destination is not of a supported type.
    """
    if isinstance(value, (str, Path)):
        return Path(value)
    if isinstance(value, BinaryIOProtocol):
        return value
    raise TypeError("Destination must be a string, a Path, or a BinaryIOProtocol")


def _validate_url(value: str) -> str:
    """Validates that the provided string is a valid URL.

    Args:
        value: The URL string to validate.

    Returns:
        The validated URL string.

    Raises:
        TypeError: If value is not a string.
        ValueError: If value is not a valid URL (missing scheme or netloc).
    """
    if not isinstance(value, str):
        raise TypeError("URL must be a string")
    parsed = urlparse(value)
    if not all([parsed.scheme, parsed.netloc]):
        raise ValueError("URL must be a valid URL")
    return value


class DummyLock:
    """A dummy lock that does nothing, used for single-threaded tasks."""

    def __enter__(self) -> bool:
        """Enters the context manager.

        Returns:
            True always.
        """
        return True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exits the context manager."""
        pass


class DownloadStatus(Enum):
    """Enumeration of possible download task statuses."""

    CANCELED = auto()
    ERROR = auto()
    FINISHED = auto()
    PENDING = auto()
    RUNNING = auto()
    UNKNOWN = auto()

    @override
    def __repr__(self) -> str:
        """Returns a string representation of the status.

        Returns:
            A string in the format 'DownloadStatus.NAME'.
        """
        return f"{self.__class__.__name__}.{self.name}"


class DownloadTask:
    """Represents a single download task.

    This class contains all information necessary to perform a download,
    including the source URL, destination, headers, and current progress.
    """

    _id_counter: count[int] = count(1)

    def __init__(
        self,
        url: str,
        dest: str | Path | BinaryIOProtocol,
        headers: Mapping[str, str] | None = None,
        kind: Literal["file", "folder"] = "file",
        progress_name: str | None = None,
    ) -> None:
        """Initializes a DownloadTask.

        Args:
            url: The source URL to download from.
            dest: The destination path (string or Path) or a binary file-like object.
            headers: Optional HTTP headers to include in the request.
            kind: Whether this is a 'file' or 'folder' download (default 'file').
            progress_name: Optional name used for progress reporting. If not provided,
                it defaults to the destination filename or URL.
        """
        self._url: str = _validate_url(url)
        self._dest: Path | BinaryIOProtocol = _validate_dest(dest)
        self._headers: dict[str, str] = dict(headers or DEFAULT_HEADERS)
        self._kind: Literal["file", "folder"] = kind

        self._cancel_event: EventProtocol = Event()
        self._id: int = next(self._id_counter)
        self._lock: AbstractContextManager[bool] = DummyLock()
        self._total: int = -1
        self._downloaded: int = 0
        self._status: DownloadStatus = DownloadStatus.PENDING

        self._progress_name: str = (
            progress_name or self._dest.name
            if isinstance(self._dest, Path)
            else self._url
        )

    # getter
    @property
    def id(self) -> int:
        """Unique identifier for the task."""
        return self._id

    @property
    def url(self) -> str:
        """The source URL."""
        return self._url

    @property
    def dest(self) -> Path | BinaryIOProtocol:
        """The destination path or file-like object."""
        return self._dest

    @property
    def headers(self) -> dict[str, str]:
        """The HTTP headers for the request."""
        return self._headers

    @property
    def kind(self) -> Literal["file", "folder"]:
        """The kind of download ('file' or 'folder')."""
        return self._kind

    @property
    def progress_name(self) -> str:
        """The name used for progress reporting."""
        return self._progress_name

    @property
    def status(self) -> DownloadStatus:
        """Current status of the download."""
        return self._status

    @property
    def total(self) -> int:
        """Total number of bytes to download. -1 if unknown."""
        return self._total

    @property
    def downloaded(self) -> int:
        """Number of bytes downloaded so far."""
        return self._downloaded

    @property
    def is_canceled(self) -> bool:
        """Whether the task has been canceled."""
        return self._cancel_event.is_set()

    # setter
    @status.setter
    def status(self, value: DownloadStatus) -> None:
        """Sets the status of the download."""
        with self._lock:
            self._status = value

    @total.setter
    def total(self, value: int) -> None:
        """Sets the total number of bytes to download."""
        with self._lock:
            self._total = value

    @downloaded.setter
    def downloaded(self, value: int) -> None:
        """Sets the number of bytes downloaded."""
        with self._lock:
            self._downloaded = value

    # method
    def cancel(self) -> None:
        """Cancels the download task."""
        with self._lock:
            self._cancel_event.set()
            self._status = DownloadStatus.CANCELED

    # setter method
    def set_cancel_event(self, value: EventProtocol) -> None:
        """Sets the event object used for cancellation.

        Args:
            value: An event object satisfying the EventProtocol.
        """
        self._cancel_event = value

    def set_lock(self, value: AbstractContextManager[bool]) -> None:
        """Sets the lock object used for thread safety.

        Args:
            value: A context manager for synchronization.
        """
        self._lock = value
