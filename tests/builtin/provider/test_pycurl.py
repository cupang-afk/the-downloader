"""Tests for builtin pycurl provider behavior."""

from pathlib import Path

import pytest
from typing import override

pytest.importorskip("pycurl")

from the_downloader.provider.pycurl import PycurlError, PycurlProvider


class FakeCurl:
    """Simulate pycurl.Curl for testing."""

    def __init__(self) -> None:
        self.perform_called: bool = False
        self.options: dict[int, object] = {}
    def setopt(self, option: int, value: object) -> None:
        """Record setopt calls."""
        self.options[option] = value

    def perform(self) -> None:
        """Simulate download."""
        self.perform_called = True

    def close(self) -> None:
        """Simulate cleanup."""


class FakeCurlError(FakeCurl):
    """Simulate a pycurl.Curl that raises during perform."""

    @override
    def perform(self) -> None:
        """Raise pycurl.error to simulate failure."""
        msg = "Failed to connect"
        raise __import__("pycurl").error(7, msg)  # pycurl.E_COULDNT_CONNECT


def test_pycurl_provider_downloads_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Download content and write to destination."""
    monkeypatch.setattr("the_downloader.provider.pycurl.Curl", lambda: FakeCurl())
    provider = PycurlProvider()
    dest = tmp_path / "out.bin"
    dest.write_text("")

    provider.download(
        "https://example.com/file.bin",
        dest,
        {},
        lambda: False,
        lambda downloaded, total, **data: None,
    )

    assert dest.exists()


def test_pycurl_provider_returns_when_canceled_before_start(
    tmp_path: Path,
) -> None:
    """Skip download when canceled before starting."""
    provider = PycurlProvider()
    dest = tmp_path / "out.bin"

    provider.download(
        "https://example.com/file.bin",
        dest,
        {},
        lambda: True,
        lambda downloaded, total, **data: None,
    )

    assert not dest.exists()


def test_pycurl_provider_raises_on_curl_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wrap pycurl.error in PycurlError."""
    monkeypatch.setattr(
        "the_downloader.provider.pycurl.Curl",
        lambda: FakeCurlError(),
    )
    provider = PycurlProvider()
    dest = tmp_path / "out.bin"
    dest.write_text("")

    with pytest.raises(PycurlError):
        provider.download(
            "https://example.com/file.bin",
            dest,
            {},
            lambda: False,
            lambda downloaded, total, **data: None,
        )
