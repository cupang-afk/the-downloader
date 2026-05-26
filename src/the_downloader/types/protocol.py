from typing import Any, Protocol, runtime_checkable


# IO
@runtime_checkable
class BinaryIOProtocol(Protocol):
    def read(self, size: int = -1, /) -> bytes: ...

    def write(self, b: bytes, /) -> int: ...

    def seek(self, offset: int, whence: int = 0, /) -> int: ...

    def tell(self) -> int: ...

    def close(self) -> None: ...

    def flush(self) -> None: ...


# provider
class CheckCanceled(Protocol):
    def __call__(self) -> bool: ...


class UpdateProgress(Protocol):
    def __call__(
        self,
        downloaded: int,
        total: int,
        **optional_data: Any,
    ) -> None: ...


# event
class EventProtocol(Protocol):
    def is_set(self) -> bool: ...
    def set(self) -> None: ...
    def clear(self) -> None: ...
