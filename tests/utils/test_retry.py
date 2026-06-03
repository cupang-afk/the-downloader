"""Tests for retry utility behavior."""

from typing import Any

import pytest

from the_downloader.utils.retry import retry


def test_retry_rejects_negative_max_retries() -> None:
    """Reject negative retry counts."""
    with pytest.raises(ValueError, match="max_retries"):
        retry(max_retries=-1)


def test_retry_rejects_negative_delay() -> None:
    """Reject negative retry delays."""
    with pytest.raises(ValueError, match="delay"):
        retry(delay=-1)


def test_retry_rejects_backoff_factor_less_than_one() -> None:
    """Reject backoff factors below one."""
    with pytest.raises(ValueError, match="backoff_factor"):
        retry(backoff_factor=0)


def test_retry_succeeds_on_first_attempt() -> None:
    """Return a successful result when the callable succeeds immediately."""
    calls = 0

    @retry(max_retries=3, delay=0)
    def subject() -> str:
        """Return a value immediately."""
        nonlocal calls
        calls += 1
        return "ok"

    result = subject()

    assert result.result == "ok"
    assert result.exceptions == []
    assert result.succeeded is True
    assert result.attempts == 1
    assert calls == 1


def test_retry_succeeds_after_failure() -> None:
    """Retry until the callable succeeds."""
    calls = 0

    @retry(max_retries=3, delay=0)
    def subject() -> str:
        """Fail once, then return a value."""
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary failure")
        return "ok"

    result = subject()

    assert result.result == "ok"
    assert len(result.exceptions) == 1
    assert isinstance(result.exceptions[0], RuntimeError)
    assert result.succeeded is True
    assert result.attempts == 2
    assert calls == 2


def test_retry_fails_after_all_attempts() -> None:
    """Return failure details when every attempt raises."""
    calls = 0

    @retry(max_retries=2, delay=0)
    def subject() -> str:
        """Always fail."""
        nonlocal calls
        calls += 1
        raise RuntimeError(f"failure {calls}")

    result = subject()

    assert result.result is None
    assert [str(error) for error in result.exceptions] == [
        "failure 1",
        "failure 2",
        "failure 3",
    ]
    assert result.succeeded is False
    assert result.attempts == 3
    assert calls == 3


def test_retry_preserves_wrapped_callable_metadata() -> None:
    """Preserve the wrapped callable metadata."""

    @retry(delay=0)
    def subject() -> str:
        """Wrapped docstring."""
        return "ok"

    assert subject.__name__ == "subject"
    assert subject.__doc__ == "Wrapped docstring."


def test_retry_uses_backoff_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sleep with exponential backoff between failed attempts."""
    sleep_calls: list[float] = []

    def fake_sleep(delay: float) -> None:
        """Record each sleep delay."""
        sleep_calls.append(delay)

    monkeypatch.setattr("the_downloader.utils.retry.sleep", fake_sleep)

    @retry(max_retries=2, delay=1, backoff_factor=2)
    def subject() -> None:
        """Always fail."""
        raise RuntimeError("failure")

    subject()

    assert sleep_calls == [1, 2, 4]


def test_retry_preserves_arguments() -> None:
    """Pass positional and keyword arguments to the wrapped callable."""

    @retry(delay=0)
    def subject(prefix: str, *, suffix: str) -> str:
        """Join the provided arguments."""
        return f"{prefix}-{suffix}"

    result = subject("left", suffix="right")

    assert result.result == "left-right"


def test_retry_rejects_invalid_callable_type() -> None:
    """Reject a decorated object that is not callable."""
    decorator = retry(delay=0)
    subject: Any = 123

    with pytest.raises(TypeError):
        decorator(subject)
