import itertools
from collections.abc import Mapping
from enum import Enum, auto
from os import PathLike
from pathlib import Path
from threading import Event, Lock
from types import MappingProxyType
from typing import BinaryIO

from .constants import DEFAULT_HEADERS

type DownloadTaskID = int


class DownloadTaskStatus(Enum):
    """Represent an enumeration of possible download task states.

    PENDING: Task is queued but not yet started
    RUNNING: Task is currently being downloaded
    COMPLETED: Task finished successfully
    CANCELED: Task was canceled by user or system
    ERROR: Task failed due to an error
    UNKNOWN: Task state is unknown or undefined
    """

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    CANCELED = auto()
    ERROR = auto()
    UNKNOWN = auto()


class DownloadTask:
    """Represent a single download operation with progress tracking.

    Attributes:
        id: Unique identifier for the download task
        url: Source URL for the download
        dest: Destination path or file-like object
        headers: HTTP headers to use for the download
        progress_name: Name to display for progress tracking
        status: Current status of the download
        downloaded: Number of bytes downloaded so far
        total: Total number of bytes to download (may be -1 if unknown)
        is_canceled: Whether the download has been canceled
    """

    __slots__ = (
        "_cancel_event",
        "_dest",
        "_downloaded",
        "_headers",
        "_id",
        "_is_file",
        "_lock",
        "_progress_name",
        "_status",
        "_total",
        "_url",
    )

    _id_counter = itertools.count(1)

    def __init__(  # noqa: PLR0913
        self,
        url: str,
        dest: str | PathLike[str] | BinaryIO,
        headers: Mapping[str, str] | None = None,
        progress_name: str | None = None,
        is_file: bool = True,
        cancel_event: Event | None = None,
    ) -> None:
        """Initialize a new download task.

        Args:
            url: Source URL for the download
            dest: Destination path or file-like object
            headers: Optional HTTP headers for the download
            progress_name: Optional name for progress display
            is_file: Whether the download is a file or not
            cancel_event: Optional cancellation event (creates new if None)

        Raises:
            TypeError: If dest is not a valid type
        """
        self._id = next(self._id_counter)
        self._url = url
        self._dest = self._validate_dest(dest)
        self._headers = (
            MappingProxyType({**DEFAULT_HEADERS, **headers})
            if headers
            else MappingProxyType(DEFAULT_HEADERS)
        )

        self._progress_name = self._validate_progress_name(progress_name)
        self._is_file = is_file
        self._status = DownloadTaskStatus.PENDING
        self._downloaded = 0
        self._total = 0
        self._cancel_event = cancel_event or Event()
        self._lock = Lock()

    def __repr__(self) -> str:
        return (
            f"<DownloadTask id={self.id}, "
            f"url={self.url}, "
            f"dest={self.dest}, "
            f"status={self.status}, "
            f"downloaded={self.downloaded}, "
            f"total={self.total}, "
            f"is_canceled={self.is_canceled}>"
        )

    def cancel(self) -> None:
        """Cancel the download operation.

        Sets the cancellation event, which should be checked by download
        providers to stop the download process.
        """
        self._cancel_event.set()

    def reset_cancel(self) -> None:
        """Reset the cancellation state.

        Clears the cancellation event, allowing the download to proceed.
        """
        self._cancel_event.clear()

    def _validate_dest(self, dest: str | PathLike[str] | BinaryIO) -> Path | BinaryIO:
        if isinstance(dest, (str, PathLike)):
            return Path(dest)  # type: ignore[arg-type]
        elif isinstance(dest, BinaryIO):
            return dest
        else:
            raise TypeError("Invalid type for dest")

    def _validate_progress_name(self, progress_name: str | None) -> str:
        if not isinstance(progress_name, str) and progress_name is not None:
            raise TypeError("Invalid type for progress_name")

        if not progress_name:
            return self.dest.name if isinstance(self.dest, Path) else self.url
        return progress_name

    @property
    def id(self) -> DownloadTaskID:
        """Get the unique identifier for this download task.

        Returns:
            Unique task ID
        """
        return self._id

    @property
    def url(self) -> str:
        """Get the source URL for the download.

        Returns:
            Download URL
        """
        return self._url

    @url.setter
    def url(self, value: str) -> None:
        """Set the source URL for the download.

        Args:
            value: New download URL

        Raises:
            TypeError: If value is not a string
        """
        if not isinstance(value, str):
            raise TypeError("Invalid type for url")
        with self._lock:
            self._url = value

    @property
    def dest(self) -> Path | BinaryIO:
        """Get the destination for the download.

        Returns:
            Destination path or file-like object
        """
        return self._dest

    @dest.setter
    def dest(self, value: Path | BinaryIO) -> None:
        """Set the destination for the download.

        Args:
            value: New destination path or file-like object

        Raises:
            TypeError: If value is not a valid destination type
        """
        with self._lock:
            self._dest = self._validate_dest(value)
            self._progress_name = self._validate_progress_name(self.progress_name)

    @property
    def headers(self) -> MappingProxyType[str, str]:
        """Get the HTTP headers for the download.

        Returns:
            Immutable mapping of HTTP headers
        """
        return self._headers

    @headers.setter
    def headers(self, value: Mapping[str, str]) -> None:
        """Set the HTTP headers for the download.

        Args:
            value: New HTTP headers mapping

        Raises:
            TypeError: If value is not a mapping
        """
        if not isinstance(value, Mapping):
            raise TypeError("Invalid type for headers")
        with self._lock:
            self._headers = MappingProxyType({**DEFAULT_HEADERS, **value})

    @property
    def progress_name(self) -> str:
        """Get the name to display for progress tracking.

        Returns:
            Progress display name or None
        """
        return self._progress_name

    @progress_name.setter
    def progress_name(self, value: str) -> None:
        """Set the name to display for progress tracking.

        Args:
            value: New progress display name

        Raises:
            TypeError: If value is not a string
        """
        if not isinstance(value, str):
            raise TypeError("Invalid type for progress_name")
        with self._lock:
            self._progress_name = value

    @property
    def is_file(self) -> bool:
        """Get the is_file flag.

        Returns:
            Whether the download is a file
        """
        return self._is_file

    @property
    def status(self) -> DownloadTaskStatus:
        """Get the current status of the download.

        Returns:
            Current download status
        """
        return self._status

    @status.setter
    def status(self, value: DownloadTaskStatus) -> None:
        """Set the current status of the download.

        Args:
            value: New download status

        Raises:
            TypeError: If value is not a DownloadTaskStatus
        """
        if not isinstance(value, DownloadTaskStatus):
            raise TypeError("Invalid type for status")
        with self._lock:
            self._status = value

    @property
    def downloaded(self) -> int:
        """Get the number of bytes downloaded so far.

        Returns:
            Number of bytes downloaded
        """
        return self._downloaded

    @downloaded.setter
    def downloaded(self, value: int) -> None:
        """Set the number of bytes downloaded so far.

        Args:
            value: New downloaded byte count

        Raises:
            TypeError: If value is not an integer
        """
        if not isinstance(value, int):
            raise TypeError("Invalid type for downloaded")
        with self._lock:
            self._downloaded = value

    @property
    def total(self) -> int:
        """Get the total number of bytes to download.

        Returns:
            Total bytes to download (-1 if unknown)
        """
        return self._total

    @total.setter
    def total(self, value: int) -> None:
        """Set the total number of bytes to download.

        Args:
            value: New total byte count

        Raises:
            TypeError: If value is not an integer
        """
        if not isinstance(value, int):
            raise TypeError("Invalid type for total")
        with self._lock:
            self._total = value

    @property
    def is_canceled(self) -> bool:
        """Check if the download has been canceled.

        Returns:
            True if download is canceled, False otherwise
        """
        return self._cancel_event.is_set()
