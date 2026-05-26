from collections.abc import Generator, Mapping
from contextlib import contextmanager
from enum import Enum, auto
from itertools import count
from pathlib import Path
from threading import Event
from types import TracebackType
from typing import ContextManager, Literal, override
from urllib.parse import urlparse

from .constants import DEFAULT_HEADERS
from .types.protocol import BinaryIOProtocol, EventProtocol


def _validate_dest(value: str | Path | BinaryIOProtocol) -> Path | BinaryIOProtocol:
    if isinstance(value, (str, Path)):
        return Path(value)
    if isinstance(value, BinaryIOProtocol):
        return value
    raise TypeError("Destination must be a string, a Path, or a BinaryIOProtocol")


def _validate_url(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("URL must be a string")
    parsed = urlparse(value)
    if not all([parsed.scheme, parsed.netloc]):
        raise ValueError("URL must be a valid URL")
    return value


class DummyLock:
    def __enter__(self) -> bool:
        return True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass


class DownloadStatus(Enum):
    CANCELED = auto()
    ERROR = auto()
    FINISHED = auto()
    PENDING = auto()
    RUNNING = auto()
    UNKNOWN = auto()

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


class DownloadTask:
    _id_counter: count[int] = count(1)

    def __init__(
        self,
        url: str,
        dest: str | Path | BinaryIOProtocol,
        headers: Mapping[str, str] | None = None,
        kind: Literal["file", "folder"] = "file",
        progress_name: str | None = None,
    ) -> None:
        self._url: str = _validate_url(url)
        self._dest: Path | BinaryIOProtocol = _validate_dest(dest)
        self._headers: dict[str, str] = dict(headers or DEFAULT_HEADERS)
        self._kind: Literal["file", "folder"] = kind

        self._cancel_event: EventProtocol = Event()
        self._id: int = next(self._id_counter)
        self._lock: ContextManager[bool] = DummyLock()
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
        return self._id

    @property
    def url(self) -> str:
        return self._url

    @property
    def dest(self) -> Path | BinaryIOProtocol:
        return self._dest

    @property
    def headers(self) -> dict[str, str]:
        return self._headers

    @property
    def kind(self) -> Literal["file", "folder"]:
        return self._kind

    @property
    def progress_name(self) -> str:
        return self._progress_name

    @property
    def status(self) -> DownloadStatus:
        return self._status

    @property
    def total(self) -> int:
        return self._total

    @property
    def downloaded(self) -> int:
        return self._downloaded

    @property
    def is_canceled(self) -> bool:
        return self._cancel_event.is_set()

    # setter
    @status.setter
    def status(self, value: DownloadStatus) -> None:
        with self._lock:
            self._status = value

    @total.setter
    def total(self, value: int) -> None:
        with self._lock:
            self._total = value

    @downloaded.setter
    def downloaded(self, value: int) -> None:
        with self._lock:
            self._downloaded = value

    # method
    def cancel(self) -> None:
        with self._lock:
            self._cancel_event.set()
            self._status = DownloadStatus.CANCELED

    @contextmanager
    def lock(self) -> Generator[bool]:
        with self._lock as ctx:
            yield ctx

    # setter method
    def set_cancel_event(self, value: EventProtocol) -> None:
        self._cancel_event = value

    def set_lock(self, value: ContextManager[bool]) -> None:
        self._lock = value
