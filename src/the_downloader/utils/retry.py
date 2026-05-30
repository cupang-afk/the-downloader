"""Retry logic utility functions."""

from collections.abc import Callable
from functools import wraps
from logging import Logger
from time import sleep
from typing import NamedTuple

from . import logger


class RetryResult[R](NamedTuple):
    """Result of a function execution with retries.

    Attributes:
        result: The return value of the function if it succeeded, otherwise None.
        exceptions: A list of exceptions encountered during all attempts.
        succeeded: Whether the function eventually succeeded.
        attempts: The total number of attempts made.
    """

    result: R | None
    exceptions: list[Exception]
    succeeded: bool
    attempts: int


def retry[R, **P](
    *,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Callable[[Callable[P, R]], Callable[P, RetryResult[R]]]:
    """Decorator that retries a function multiple times upon failure.

    Args:
        max_retries: Maximum number of retries (excluding initial attempt).
        delay: Initial delay between retries in seconds.
        backoff_factor: Factor by which the delay increases after each failure.

    Returns:
        A decorator that wraps the function and returns a RetryResult.

    Raises:
        ValueError: If arguments are invalid.
    """
    if max_retries < 0:
        raise ValueError("max_retries must be greater than or equal to 0")
    if delay < 0:
        raise ValueError("delay must be greater than or equal to 0")
    if backoff_factor < 1:
        raise ValueError("backoff_factor must be greater than or equal to 1")

    def decorator(inner_func: Callable[P, R]) -> Callable[P, RetryResult[R]]:
        """Wrap a callable with retry behavior."""

        @wraps(inner_func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> RetryResult[R]:
            """Run the wrapped callable and collect retry results."""
            _logger: Logger = (
                logger.get_logger().getChild("retry").getChild(inner_func.__name__)
            )
            exceptions: list[Exception] = []
            current_delay = delay

            for attempt in range(1, max_retries + 2):
                try:
                    result = inner_func(*args, **kwargs)
                    if attempt == 1:
                        _logger.info("Succeeded on first attempt")
                    else:
                        _logger.info("Succeeded after %d attempt(s)", attempt)
                    return RetryResult(
                        result=result,
                        exceptions=exceptions,
                        succeeded=True,
                        attempts=attempt,
                    )
                except Exception as e:
                    exceptions.append(e)
                    _logger.warning(
                        "Attempt %d/%d failed: %s",
                        attempt,
                        max_retries + 1,
                        e,
                    )

                    if current_delay > 0:
                        sleep(current_delay)
                    current_delay *= backoff_factor
            _logger.error("All %d attempts failed", max_retries + 1)
            return RetryResult(
                result=None,
                exceptions=exceptions,
                succeeded=False,
                attempts=max_retries + 1,
            )

        return wrapper

    return decorator
