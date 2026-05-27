"""Protocols for the downloader."""

from typing import Any, Protocol, runtime_checkable


# IO
@runtime_checkable
class BinaryIOProtocol(Protocol):
    """Protocol for binary IO objects."""

    def read(self, size: int = -1, /) -> bytes:
        """Read bytes from the IO object."""
        ...

    def write(self, b: bytes, /) -> int:
        """Write bytes to the IO object."""
        ...

    def seek(self, offset: int, whence: int = 0, /) -> int:
        """Seek to a position in the IO object."""
        ...

    def tell(self) -> int:
        """Get the current position in the IO object."""
        ...

    def close(self) -> None:
        """Close the IO object."""
        ...

    def flush(self) -> None:
        """Flush the IO object."""
        ...


# provider
class CheckCanceled(Protocol):
    """Protocol for checking if a download is canceled."""

    def __call__(self) -> bool:
        """Check if the download is canceled."""
        ...


class UpdateProgress(Protocol):
    """Protocol for updating download progress."""

    def __call__(
        self,
        downloaded: int,
        total: int,
        **optional_data: Any,
    ) -> None:
        """Update the download progress.

        Args:
            downloaded: The number of bytes downloaded so far.
            total: The total number of bytes to download.
            **optional_data: Additional optional data from the provider.
        """
        ...


# event
class EventProtocol(Protocol):
    """Protocol for event objects."""

    def is_set(self) -> bool:
        """Check if the event is set."""
        ...

    def set(self) -> None:
        """Set the event."""
        ...

    def clear(self) -> None:
        """Clear the event."""
        ...
