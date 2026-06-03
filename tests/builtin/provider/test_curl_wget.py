"""Tests for builtin subprocess stream providers."""

from collections.abc import Callable
from pathlib import Path, PurePath
from typing import Any, override

import pytest

from the_downloader.provider.curl import CurlProvider
from the_downloader.provider.wget import WgetProvider


class FakeStdout:
    """Small stdout stream for subprocess provider tests."""

    def __init__(self, chunks: list[bytes]) -> None:
        """Initialize chunks."""
        self.chunks: list[bytes] = chunks

    def read(self, size: int = -1) -> bytes:
        """Read next chunk."""
        if size == 0 or not self.chunks:
            return b""
        return self.chunks.pop(0)


class FakeProcess:
    """Small process object with stdout."""

    def __init__(self, chunks: list[bytes]) -> None:
        """Initialize process stdout."""
        self.stdout: FakeStdout = FakeStdout(chunks)


class FakePopenContext:
    """Context manager returned by fake popen_wrapper."""

    def __init__(self, process: FakeProcess) -> None:
        """Initialize fake context."""
        self.process: FakeProcess = process

    def __enter__(self) -> FakeProcess:
        """Enter context."""
        return self.process

    def __exit__(self, *args: object) -> None:
        """Exit context."""


class FakeCurlProvider(CurlProvider):
    """Curl provider with fake subprocess output."""

    def __init__(self, chunks: list[bytes]) -> None:
        """Initialize fake curl provider."""
        super().__init__("curl")
        self.commands: list[list[str]] = []
        self._bin: Path = Path("curl")
        self._chunk_size: int = 2
        self._timeout: int = 3
        self._ca_cert_path: str = "cert.pem"
        self.chunks: list[bytes] = chunks

    @override
    def popen_wrapper(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        command: list[str],
        raise_non_zero_return: bool = True,
        terminate_timeout: int = 10,
        **kwargs: Any,
    ) -> FakePopenContext:
        """Return fake process context."""
        self.commands.append(command)
        return FakePopenContext(FakeProcess(self.chunks.copy()))


class FakeWgetProvider(WgetProvider):
    """Wget provider with fake subprocess output."""

    def __init__(self, chunks: list[bytes]) -> None:
        """Initialize fake wget provider."""
        super().__init__("wget")
        self.commands: list[list[str]] = []
        self._bin: Path = Path("wget")
        self._chunk_size: int = 2
        self._timeout: int = 3
        self._ca_cert_path: str = "cert.pem"
        self.chunks: list[bytes] = chunks

    @override
    def popen_wrapper(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        command: list[str],
        raise_non_zero_return: bool = True,
        terminate_timeout: int = 10,
        **kwargs: Any,
    ) -> FakePopenContext:
        """Return fake process context."""
        self.commands.append(command)
        return FakePopenContext(FakeProcess(self.chunks.copy()))


def fake_total_size(session: object, url: str, headers: dict[str, str]) -> int:
    """Return a stable total size for subprocess provider tests."""
    assert session is not None
    assert url
    assert isinstance(headers, dict)
    return 4


@pytest.mark.parametrize(
    ("provider_factory", "binary_name"),
    [(FakeCurlProvider, "curl"), (FakeWgetProvider, "wget")],
)
def test_subprocess_stream_provider_downloads_chunks(
    provider_factory: Callable[
        [list[bytes]],
        FakeCurlProvider | FakeWgetProvider,
    ],
    binary_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Download chunks from subprocess stdout."""
    monkeypatch.setattr(
        "the_downloader.provider.curl.get_total_size",
        fake_total_size,
    )
    monkeypatch.setattr(
        "the_downloader.provider.wget.get_total_size",
        fake_total_size,
    )
    provider = provider_factory([b"ab", b"cd"])
    dest = tmp_path / "file.bin"
    progress: list[tuple[int, int]] = []

    provider.download(
        "https://example.com/file.bin",
        PurePath(dest),
        {"Header": "Value"},
        lambda: False,
        lambda downloaded, total, **data: progress.append((downloaded, total)),
    )

    assert dest.read_bytes() == b"abcd"
    assert progress == [(2, 4), (4, 4)]
    assert provider.commands[0][0] == binary_name


def test_subprocess_stream_provider_returns_when_canceled(
    tmp_path: Path,
) -> None:
    """Skip subprocess work when canceled before start."""
    provider = FakeCurlProvider([b"ab"])
    dest = tmp_path / "file.bin"

    provider.download(
        "https://example.com/file.bin",
        PurePath(dest),
        {},
        lambda: True,
        lambda downloaded, total, **data: None,
    )

    assert not dest.exists()
    assert provider.commands == []
