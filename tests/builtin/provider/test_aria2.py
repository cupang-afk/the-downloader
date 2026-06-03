"""Tests for builtin aria2 provider behavior."""

from pathlib import Path, PurePath
from typing import Any, cast

import pytest

from the_downloader.provider.aria2 import Aria2Error, Aria2Provider


class FakeAria2Api:
    """Small aria2 RPC API fake."""

    def __init__(self) -> None:
        """Initialize RPC call state."""
        self.add_uri_calls: list[tuple[str, list[str], dict[str, Any]]] = []
        self.removed: list[str] = []
        self.removed_results: list[str] = []

    def addUri(
        self,
        token: str,
        urls: list[str],
        options: dict[str, Any],
    ) -> str:
        """Record addUri and return a fake gid."""
        self.add_uri_calls.append((token, urls, options))
        return "gid-1"

    def remove(self, token: str, gid: str) -> None:
        """Record remove calls."""
        self.removed.append(f"{token}:{gid}")

    def removeDownloadResult(self, token: str, gid: str) -> None:
        """Record removeDownloadResult calls."""
        self.removed_results.append(f"{token}:{gid}")

    def tellStatus(
        self,
        token: str,
        gid: str,
        keys: list[str],
    ) -> dict[str, str]:
        """Return a completed download status."""
        assert token
        assert gid == "gid-1"
        assert "status" in keys
        return {
            "status": "complete",
            "completedLength": "5",
            "totalLength": "10",
        }


class FakeServer:
    """Small XML-RPC server fake."""

    def __init__(self) -> None:
        """Initialize fake aria2 namespace."""
        self.aria2: FakeAria2Api = FakeAria2Api()


def ignore_delete(path: object) -> None:
    """Ignore aria2 sidecar cleanup."""
    assert path is not None


def ignore_progress(downloaded: int, total: int, **data: object) -> None:
    """Ignore progress updates."""
    assert downloaded >= 0
    assert total >= 0
    assert isinstance(data, dict)


def record_progress(
    progress: list[tuple[int, int]],
) -> object:
    """Build a progress callback that records updates."""

    def update_progress(downloaded: int, total: int, **data: object) -> None:
        """Record a progress update."""
        assert isinstance(data, dict)
        progress.append((downloaded, total))

    return update_progress


def resolve_binary_path(path: object) -> Path:
    """Return a fake resolved aria2 path."""
    assert path == "aria2c"
    return Path("aria2c")


def test_aria2_provider_initializes_binary_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolve the aria2 binary path during construction."""
    monkeypatch.setattr(
        "the_downloader.provider.aria2.resolve_binary",
        resolve_binary_path,
    )

    provider = Aria2Provider("aria2c")

    binary_path = provider._bin  # pyright: ignore[reportPrivateUsage]
    assert binary_path == Path("aria2c")


def test_aria2_provider_rejects_download_without_rpc_server(
    tmp_path: Path,
) -> None:
    """Reject downloads when the RPC server has not been started."""
    provider = cast(Any, Aria2Provider.__new__(Aria2Provider))
    provider._rpc_server = None

    with pytest.raises(Aria2Error, match="RPC server"):
        provider.download(
            "https://example.com/file.zip",
            PurePath(tmp_path / "file.zip"),
            {},
            lambda: False,
            ignore_progress,
        )


def test_aria2_provider_download_reports_progress_and_cleans_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Submit an RPC download, report progress, and remove the result."""
    fake_server = FakeServer()
    provider = cast(Any, Aria2Provider.__new__(Aria2Provider))
    provider._rpc_server = fake_server
    provider._rpc_token = "token:secret"
    monkeypatch.setattr(
        "the_downloader.provider.aria2.delete",
        ignore_delete,
    )
    progress: list[tuple[int, int]] = []

    provider.download(
        "https://example.com/file.zip",
        PurePath(tmp_path / "file.zip"),
        {"Header": "Value"},
        lambda: False,
        record_progress(progress),
    )

    assert progress == [(5, 10)]
    assert fake_server.aria2.add_uri_calls[0][1] == [
        "https://example.com/file.zip",
    ]
    assert fake_server.aria2.removed_results == ["token:secret:gid-1"]


def test_aria2_provider_download_removes_active_download_when_canceled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remove active RPC downloads when cancellation is requested."""
    fake_server = FakeServer()
    provider = cast(Any, Aria2Provider.__new__(Aria2Provider))
    provider._rpc_server = fake_server
    provider._rpc_token = "token:secret"
    monkeypatch.setattr(
        "the_downloader.provider.aria2.delete",
        ignore_delete,
    )

    provider.download(
        "https://example.com/file.zip",
        PurePath(tmp_path / "file.zip"),
        {},
        lambda: True,
        ignore_progress,
    )

    assert fake_server.aria2.removed == ["token:secret:gid-1"]
