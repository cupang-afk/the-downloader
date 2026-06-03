"""Tests for metadata utility behavior."""

from collections.abc import Mapping
from typing import Any

import pytest
import requests

from the_downloader.utils.metadata import get_total_size


class FakeResponse:
    """Minimal response object for metadata tests."""

    def __init__(
        self,
        headers: Mapping[str, str],
        error: requests.RequestException | None = None,
    ) -> None:
        """Initialize the fake response."""
        self.headers: Mapping[str, str] = headers
        self._error: requests.RequestException | None = error

    def raise_for_status(self) -> None:
        """Raise the configured request error if one exists."""
        if self._error is not None:
            raise self._error


class FakeSession:
    """Minimal session object for metadata tests."""

    def __init__(self, response: FakeResponse) -> None:
        """Initialize the fake session."""
        self.response: FakeResponse = response
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Record the GET request and return the configured response."""
        self.calls.append({"url": url, **kwargs})
        return self.response


def test_get_total_size_content_length() -> None:
    """Return the response Content-Length as an integer."""
    expected_total = 123
    session = FakeSession(FakeResponse({"Content-Length": str(expected_total)}))
    headers = {"User-Agent": "test"}

    result = get_total_size(
        session,  # pyright: ignore[reportArgumentType]
        "https://example.com/file.zip",
        headers,
    )

    assert result == expected_total
    assert session.calls == [
        {
            "url": "https://example.com/file.zip",
            "headers": headers,
            "stream": True,
            "allow_redirects": True,
        }
    ]


def test_get_total_size_missing_content_length() -> None:
    """Return -1 when Content-Length is missing."""
    session = FakeSession(FakeResponse({}))

    result = get_total_size(
        session,  # pyright: ignore[reportArgumentType]
        "https://example.com/file.zip",
        {},
    )

    assert result == -1


def test_get_total_size_request_error() -> None:
    """Return -1 when the request fails with a requests exception."""
    response = FakeResponse({}, requests.HTTPError("bad status"))
    session = FakeSession(response)

    result = get_total_size(
        session,  # pyright: ignore[reportArgumentType]
        "https://example.com/file.zip",
        {},
    )

    assert result == -1


def test_get_total_size_invalid_content_length() -> None:
    """Reject Content-Length values that cannot be parsed as integers."""
    session = FakeSession(FakeResponse({"Content-Length": "unknown"}))

    with pytest.raises(ValueError):
        get_total_size(
            session,  # pyright: ignore[reportArgumentType]
            "https://example.com/file.zip",
            {},
        )
