"""Tests for builtin requests provider behavior."""

from collections.abc import Iterable
from pathlib import Path

import pytest
from typing import override

from the_downloader.provider.requests import RequestsError, RequestsProvider


class FakeResponse:
    """Small response object for requests provider tests."""

    def __init__(self, chunks: Iterable[bytes], total: str = "4") -> None:
        """Initialize fake response content."""
        self.headers: dict[str, str] = {"Content-Length": total}
        self.chunks: list[bytes] = list(chunks)

    def iter_content(self, chunk_size: int) -> Iterable[bytes]:
        """Yield response chunks."""
        assert chunk_size > 0
        yield from self.chunks

    def raise_for_status(self) -> None:
        """Return successful status."""


class FailingResponse(FakeResponse):
    """Response that fails status validation."""

    @override
    def raise_for_status(self) -> None:
        """Raise a status error."""
        raise RuntimeError("bad status")


class FakeSession:
    """Small session object for requests provider tests."""

    def __init__(self, response: FakeResponse) -> None:
        """Initialize fake session response."""
        self.response: FakeResponse = response
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, **kwargs: object) -> FakeResponse:
        """Record GET calls and return response."""
        self.calls.append({"url": url, **kwargs})
        return self.response


def test_requests_provider_downloads_chunks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Download non-empty response chunks and report progress."""
    session = FakeSession(FakeResponse([b"ab", b"", b"cd"]))
    monkeypatch.setattr(
        "the_downloader.provider.requests.get_requests_session",
        lambda: session,
    )
    provider = RequestsProvider()
    dest = tmp_path / "file.bin"
    progress: list[tuple[int, int]] = []

    provider.download(
        "https://example.com/file.bin",
        dest,
        {"User-Agent": "test"},
        lambda: False,
        lambda downloaded, total, **data: progress.append((downloaded, total)),
    )

    assert dest.read_bytes() == b"abcd"
    assert progress == [(2, 4), (4, 4)]
    assert session.calls[0]["stream"] is True
    assert session.calls[0]["allow_redirects"] is True


def test_requests_provider_returns_when_canceled_before_start(
    tmp_path: Path,
) -> None:
    """Skip requests when canceled before starting."""
    provider = RequestsProvider()
    dest = tmp_path / "file.bin"

    provider.download(
        "https://example.com/file.bin",
        dest,
        {},
        lambda: True,
        lambda downloaded, total, **data: None,
    )

    assert not dest.exists()


def test_requests_provider_wraps_request_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wrap request failures in RequestsError."""
    monkeypatch.setattr(
        "the_downloader.provider.requests.get_requests_session",
        lambda: FakeSession(FailingResponse([])),
    )
    provider = RequestsProvider()

    with pytest.raises(RequestsError):
        provider.download(
            "https://example.com/file.bin",
            tmp_path / "file.bin",
            {},
            lambda: False,
            lambda downloaded, total, **data: None,
        )
