"""Download task dataclass for defining download parameters."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": "Downloader/1.0",
}


@dataclass
class DownloadTask:
    """Represents a download task with URL, destination, and metadata.

    Attributes:
        url: The URL to download from.
        dest: The destination path or file-like object.
        headers: HTTP headers for the request.
        progress_name: Name displayed in progress callbacks.
    """

    url: str
    dest: IO[bytes] | Path
    headers: dict[str, str] = field(default_factory=lambda: DEFAULT_HEADERS.copy())
    progress_name: str | None = None

    def __post_init__(self) -> None:
        """Initializes derived attributes after dataclass initialization."""
        # Merge with default headers
        self.headers = {**DEFAULT_HEADERS, **self.headers}
        # Set progress name if not provided
        if not self.progress_name:
            if isinstance(self.dest, Path):
                self.progress_name = self.dest.name
            else:
                self.progress_name = self.url

    def copy(
        self,
        url: str | None = None,
        dest: IO[bytes] | Path | None = None,
        headers: dict[str, str] | None = None,
        progress_name: str | None = None,
    ) -> "DownloadTask":
        """Creates a copy of the task with optional overrides.

        Args:
            url: New URL, or None to keep current.
            dest: New destination, or None to keep current.
            headers: New headers, or None to keep current.
            progress_name: New progress name, or None to keep current.

        Returns:
            A new DownloadTask instance with the specified overrides.
        """
        return self.__class__(
            url=url or self.url,
            dest=dest or self.dest,
            headers=headers or self.headers,
            progress_name=progress_name or self.progress_name,
        )
