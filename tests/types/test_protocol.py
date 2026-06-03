"""Tests for runtime-checkable protocol behavior."""

from the_downloader.types.protocol import BinaryIOProtocol, EventProtocol


class CompleteBinaryIO:
    """Object that provides every binary IO protocol method."""

    def close(self) -> None:
        """Close the object."""

    def flush(self) -> None:
        """Flush pending data."""

    def read(self, size: int = -1, /) -> bytes:
        """Read bytes from the object."""
        if size < 0:
            return b""
        return b""

    def seek(self, offset: int, whence: int = 0, /) -> int:
        """Seek to a position."""
        return offset + whence

    def tell(self) -> int:
        """Return the current position."""
        return 0

    def write(self, b: bytes, /) -> int:
        """Write bytes to the object."""
        return len(b)


class CompleteEvent:
    """Object that provides every event protocol method."""

    def __init__(self) -> None:
        """Initialize event state."""
        self.value: bool = False

    def clear(self) -> None:
        """Clear event state."""
        self.value = False

    def is_set(self) -> bool:
        """Return event state."""
        return self.value

    def set(self) -> None:
        """Set event state."""
        self.value = True


class MissingBinaryIOMethod:
    """Object missing required binary IO protocol methods."""

    def read(self, size: int = -1, /) -> bytes:
        """Read bytes from the object."""
        if size < 0:
            return b""
        return b""


class MissingEventMethod:
    """Object missing required event protocol methods."""

    def is_set(self) -> bool:
        """Return event state."""
        return False


def test_binary_io_protocol_accepts_complete_object() -> None:
    """Accept objects that provide every binary IO method at runtime."""
    assert isinstance(CompleteBinaryIO(), BinaryIOProtocol)


def test_binary_io_protocol_rejects_incomplete_object() -> None:
    """Reject objects missing required binary IO methods at runtime."""
    assert not isinstance(MissingBinaryIOMethod(), BinaryIOProtocol)


def test_event_protocol_accepts_complete_object() -> None:
    """Accept objects that provide every event method at runtime."""
    assert isinstance(CompleteEvent(), EventProtocol)


def test_event_protocol_rejects_incomplete_object() -> None:
    """Reject objects missing required event methods at runtime."""
    assert not isinstance(MissingEventMethod(), EventProtocol)
