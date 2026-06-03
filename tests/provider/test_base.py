"""Tests for base provider behavior."""

from abc import ABC
from collections.abc import Sequence
from pathlib import PurePath
from typing import Any, cast, override

import pytest

from the_downloader.provider.base import (
    DEFAULT_CA_CERT_PATH,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_TIMEOUT,
    BaseProvider,
    ProviderSubprocessMixin,
)
from the_downloader.types.protocol import CheckCanceled, UpdateProgress


class CompleteProvider(BaseProvider):
    """Concrete provider for base provider tests."""

    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        """Record a progress update."""
        if not check_canceled():
            update_progress(len(url), len(str(dest)) + len(headers))


class MissingDownloadProvider(BaseProvider, ABC):
    """Incomplete provider missing download implementation."""


class RecordingMixin(ProviderSubprocessMixin):
    """Mixin test harness that records process cleanup."""

    def __init__(self) -> None:
        """Initialize cleanup call state."""
        self.cleanup_calls: list[tuple[object, bool, int]] = []

    @override
    def popen_terminate(
        self,
        process: Any,
        raise_nonzero_return: bool,
        terminate_timeout: int,
    ) -> None:
        """Record cleanup arguments."""
        self.cleanup_calls.append(
            (process, raise_nonzero_return, terminate_timeout),
        )


class FakePopen:
    """Small subprocess.Popen replacement for wrapper tests."""

    created: list["FakePopen"] = []

    def __class_getitem__(cls, item: object) -> type["FakePopen"]:
        """Support runtime subscription used by subprocess.Popen annotations."""
        return cls

    def __init__(
        self,
        command: Sequence[str],
        text: bool,
        **kwargs: Any,
    ) -> None:
        """Initialize fake process state."""
        self.args: list[str] = list(command)
        self.kwargs: dict[str, Any] = kwargs
        self.pid: int = 12345
        self.returncode: int = 0
        self.text: bool = text
        FakePopen.created.append(self)


def test_base_provider_rejects_direct_instantiation() -> None:
    """Reject direct instantiation because download is abstract."""
    provider_type = type("RuntimeBaseProvider", (BaseProvider,), {})

    with pytest.raises(TypeError, match="abstract"):
        provider_type()


def test_base_provider_rejects_incomplete_subclass() -> None:
    """Reject subclasses that do not implement download."""
    provider_type = type(
        "RuntimeMissingDownloadProvider",
        (MissingDownloadProvider,),
        {},
    )

    with pytest.raises(TypeError, match="abstract"):
        provider_type()


def test_base_provider_initializes_defaults() -> None:
    """Initialize provider defaults."""
    provider = CompleteProvider()

    assert provider.chunk_size == DEFAULT_CHUNK_SIZE
    assert provider.timeout == DEFAULT_TIMEOUT
    assert provider.ca_cert_path == DEFAULT_CA_CERT_PATH


def test_base_provider_initializes_custom_values() -> None:
    """Initialize provider custom values."""
    provider = CompleteProvider(
        chunk_size=10,
        timeout=20,
        ca_cert_path="cert.pem",
    )

    assert provider.chunk_size == 10
    assert provider.timeout == 20
    assert provider.ca_cert_path == "cert.pem"


def test_base_provider_hooks_are_noops() -> None:
    """Run default hooks without errors or return values."""
    provider = CompleteProvider()

    assert provider.__pre_hook__() is None
    assert provider.__post_hook__() is None


def test_base_provider_get_logger_names_child_logger() -> None:
    """Return a logger named after the provider class."""
    provider = CompleteProvider()

    assert provider.get_logger().name.endswith("CompleteProvider")


def test_provider_subprocess_mixin_rejects_negative_terminate_timeout() -> None:
    """Reject negative process termination timeouts."""
    mixin = ProviderSubprocessMixin()

    with pytest.raises(ValueError, match="terminate_timeout"):
        mixin.popen_terminate(
            FakePopen(  # pyright: ignore[reportArgumentType]
                ["cmd"],
                text=False,
            ),
            raise_nonzero_return=False,
            terminate_timeout=-1,
        )


def test_provider_subprocess_mixin_wrapper_starts_and_cleans_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Start a process and clean it up when the context exits."""
    FakePopen.created.clear()
    monkeypatch.setattr(
        "the_downloader.provider.base.subprocess.Popen",
        FakePopen,
    )
    mixin = RecordingMixin()

    with mixin.popen_wrapper(
        ["cmd"],
        raise_non_zero_return=False,
        terminate_timeout=7,
    ) as process:
        assert process is FakePopen.created[0]

    assert mixin.cleanup_calls == [(FakePopen.created[0], False, 7)]
    assert FakePopen.created[0].kwargs["stdout"] is not None
    assert FakePopen.created[0].kwargs["stdin"] is not None


def test_provider_subprocess_mixin_wrapper_passes_text_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass text mode through to the subprocess constructor."""
    FakePopen.created.clear()
    monkeypatch.setattr(
        "the_downloader.provider.base.subprocess.Popen",
        FakePopen,
    )
    mixin = RecordingMixin()

    with mixin.popen_wrapper(["cmd"], text=True) as process:
        assert cast(FakePopen, cast(object, process)).text is True

    assert mixin.cleanup_calls == [
        (FakePopen.created[0], True, DEFAULT_TIMEOUT),
    ]
