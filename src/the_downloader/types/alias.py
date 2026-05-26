from types import TracebackType

type ExcInfo = tuple[type[BaseException], BaseException, TracebackType | None]
