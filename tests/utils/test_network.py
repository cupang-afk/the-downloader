"""Tests for network utility behavior."""

from types import TracebackType
from typing import Self

import pytest

from the_downloader.utils.network import check_open_port

AF_INET = 2
SOCK_STREAM = 1
TEST_PORT = 12345
TEST_TIMEOUT = 1


class FakeSocket:
    """Minimal socket object for network tests."""

    bind_error: OSError | None
    bind_calls: list[tuple[str, int]]
    timeout: float | None

    def __init__(self, bind_error: OSError | None = None) -> None:
        """Initialize the fake socket."""
        self.bind_error = bind_error
        self.bind_calls = []
        self.timeout = None

    def __enter__(self) -> Self:
        """Enter the socket context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the socket context manager."""
        return None

    def bind(self, address: tuple[str, int]) -> None:
        """Record the bind address and raise the configured error."""
        self.bind_calls.append(address)
        if self.bind_error is not None:
            raise self.bind_error

    def settimeout(self, timeout: float) -> None:
        """Record the configured timeout."""
        self.timeout = timeout


def test_check_open_port_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return true when the socket can bind to the port."""
    fake_socket = FakeSocket()

    def fake_socket_factory(family: int, kind: int) -> FakeSocket:
        """Return the fake socket for the expected socket parameters."""
        assert family == AF_INET
        assert kind == SOCK_STREAM
        return fake_socket

    monkeypatch.setattr(
        "the_downloader.utils.network.socket.socket",
        fake_socket_factory,
    )

    result = check_open_port(TEST_PORT, "127.0.0.1")

    assert result is True
    assert fake_socket.timeout == TEST_TIMEOUT
    assert fake_socket.bind_calls == [("127.0.0.1", TEST_PORT)]


def test_check_open_port_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return false when the socket cannot bind to the port."""
    fake_socket = FakeSocket(OSError("port in use"))

    def fake_socket_factory(family: int, kind: int) -> FakeSocket:
        """Return the fake socket for the expected socket parameters."""
        assert family == AF_INET
        assert kind == SOCK_STREAM
        return fake_socket

    monkeypatch.setattr(
        "the_downloader.utils.network.socket.socket",
        fake_socket_factory,
    )

    result = check_open_port(TEST_PORT, "127.0.0.1")

    assert result is False
    assert fake_socket.timeout == TEST_TIMEOUT
    assert fake_socket.bind_calls == [("127.0.0.1", TEST_PORT)]


def test_check_open_port_default_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bind to all interfaces when no host is provided."""
    fake_socket = FakeSocket()

    def fake_socket_factory(family: int, kind: int) -> FakeSocket:
        """Return the fake socket for the expected socket parameters."""
        assert family == AF_INET
        assert kind == SOCK_STREAM
        return fake_socket

    monkeypatch.setattr(
        "the_downloader.utils.network.socket.socket",
        fake_socket_factory,
    )

    result = check_open_port(TEST_PORT)

    assert result is True
    assert fake_socket.bind_calls == [("", TEST_PORT)]


def test_check_open_port_rejects_invalid_port_type() -> None:
    """Reject a port that is not integer-like."""
    with pytest.raises(TypeError):
        check_open_port("not-a-port")  # pyright: ignore[reportArgumentType]
