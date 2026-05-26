from collections.abc import Callable
from functools import wraps
from time import sleep
from typing import NamedTuple


class RetryResult[R](NamedTuple):
    result: R | None
    exceptions: list[Exception]
    succeeded: bool
    attempts: int


def retry[R, **P](
    *,
    max_retries: int,
    delay: float,
    backoff_factor: float = 2.0,
) -> Callable[[Callable[P, R]], Callable[P, RetryResult[R]]]:
    if max_retries < 0:
        raise ValueError("max_retries must be greater than or equal to 0")
    if delay < 0:
        raise ValueError("delay must be greater than or equal to 0")
    if backoff_factor < 1:
        raise ValueError("backoff_factor must be greater than or equal to 1")

    def decorator(inner_func: Callable[P, R]) -> Callable[P, RetryResult[R]]:
        @wraps(inner_func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> RetryResult[R]:
            exceptions: list[Exception] = []
            current_delay = delay

            for attempt in range(1, max_retries + 2):
                try:
                    return RetryResult(
                        result=inner_func(*args, **kwargs),
                        exceptions=exceptions,
                        succeeded=True,
                        attempts=attempt,
                    )
                except Exception as e:
                    exceptions.append(e)

                    if current_delay > 0:
                        sleep(current_delay)
                    current_delay *= backoff_factor
            return RetryResult(
                result=None,
                exceptions=exceptions,
                succeeded=False,
                attempts=max_retries + 1,
            )

        return wrapper

    return decorator


if __name__ == "__main__":

    @retry(max_retries=3, delay=0)
    def succeeds() -> str:
        return "ok"

    success = succeeds()
    assert success.result == "ok"
    assert success.exceptions == []
    assert success.succeeded is True
    assert success.attempts == 1

    attempts = 0

    @retry(max_retries=3, delay=0)
    def succeeds_after_retries() -> str:
        global attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("not yet")
        return "ok"

    eventual_success = succeeds_after_retries()
    assert eventual_success.result == "ok"
    assert eventual_success.succeeded is True
    assert eventual_success.attempts == 3
    assert len(eventual_success.exceptions) == 2
    assert all(
        isinstance(exception, RuntimeError) for exception in eventual_success.exceptions
    )

    @retry(max_retries=2, delay=0)
    def always_fails() -> str:
        raise ValueError("nope")

    failure = always_fails()
    assert failure.result is None
    assert failure.succeeded is False
    assert failure.attempts == 3
    assert len(failure.exceptions) == 3
    assert all(isinstance(exception, ValueError) for exception in failure.exceptions)

    print("retry.py tests passed")
