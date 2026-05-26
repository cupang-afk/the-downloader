import os
import subprocess
from abc import ABCMeta, abstractmethod
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from functools import cache
from logging import Logger
from pathlib import PurePath
from typing import Any, Literal, cast, final, overload

import psutil

from ..constants import DEFAULT_CA_CERT_PATH, DEFAULT_CHUNK_SIZE, DEFAULT_TIMEOUT
from ..logger import logger
from ..types.protocol import CheckCanceled, UpdateProgress


@cache
def _get_cached_logger(name: str) -> Logger:
    return logger.getChild(name)


class BaseProvider(metaclass=ABCMeta):
    def __init__(
        self,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        timeout: int = DEFAULT_TIMEOUT,
        ca_cert_path: str = DEFAULT_CA_CERT_PATH,
    ) -> None:
        self._chunk_size: int = chunk_size
        self._timeout: int = timeout
        self._ca_cert_path: str = ca_cert_path

    @property
    def chunk_size(self) -> int:
        return self._chunk_size

    @property
    def timeout(self) -> int:
        return self._timeout

    @property
    def ca_cert_path(self) -> str:
        return self._ca_cert_path

    # hook
    def __pre_hook__(self) -> None:
        return

    def __post_hook__(self) -> None:
        return

    # method
    @final
    def get_logger(self) -> Logger:
        return _get_cached_logger(type(self).__name__)

    # abstract method
    @abstractmethod
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        raise NotImplementedError


class ProviderSubprocessMixin:
    @overload
    @contextmanager
    def popen_wrapper(
        self,
        command: Sequence[str],
        text: Literal[True],
        raise_non_zero_return: bool = True,
        terminate_timeout: int = DEFAULT_TIMEOUT,
        **kwargs: Any,
    ) -> Generator[subprocess.Popen[str]]: ...

    @overload
    @contextmanager
    def popen_wrapper(
        self,
        command: Sequence[str],
        text: Literal[False] = False,
        raise_non_zero_return: bool = True,
        terminate_timeout: int = DEFAULT_TIMEOUT,
        **kwargs: Any,
    ) -> Generator[subprocess.Popen[bytes]]: ...

    @contextmanager
    def popen_wrapper(
        self,
        command: Sequence[str],
        raise_non_zero_return: bool = True,
        terminate_timeout: int = DEFAULT_TIMEOUT,
        **kwargs: Any,
    ) -> Generator[subprocess.Popen[str] | subprocess.Popen[bytes]]:
        kwargs.setdefault("stdout", subprocess.PIPE)
        kwargs.setdefault("stderr", subprocess.DEVNULL)
        kwargs.setdefault("stdin", subprocess.DEVNULL)

        # cSpell: words creationflags
        if os.name == "nt":
            kwargs.setdefault("creationflags", subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            kwargs.setdefault("start_new_session", True)
        process: subprocess.Popen[str] | subprocess.Popen[bytes]
        text: bool = bool(kwargs.pop("text", False))
        if text:
            process = subprocess.Popen(
                command,
                text=text,
                **kwargs,
            )
        else:
            process = cast(
                subprocess.Popen[bytes],
                subprocess.Popen(
                    command,
                    text=text,
                    **kwargs,
                ),
            )
        try:
            yield process
        finally:
            self.popen_terminate(
                process,
                raise_nonzero_return=raise_non_zero_return,
                terminate_timeout=terminate_timeout,
            )

    def popen_terminate(
        self,
        process: subprocess.Popen[str] | subprocess.Popen[bytes],
        raise_nonzero_return: bool,
        terminate_timeout: int,
    ) -> None:
        if terminate_timeout < 0:
            raise ValueError("terminate_timeout must be >= 0")

        stdout: str | bytes | None = None
        stderr: str | bytes | None = None

        if process.poll() is None:
            try:
                parent = psutil.Process(process.pid)
                processes = parent.children(recursive=True)
                processes.append(parent)
            except psutil.NoSuchProcess:
                processes = []

            for proc in processes:
                try:
                    proc.terminate()
                except psutil.NoSuchProcess:
                    pass

            # cSpell: words  procs
            _, alive = psutil.wait_procs(processes, timeout=terminate_timeout)

            for proc in alive:
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass

            psutil.wait_procs(alive, timeout=terminate_timeout)

        try:
            stdout, stderr = process.communicate(timeout=0)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

        if (
            process.returncode is not None
            and process.returncode != 0
            and raise_nonzero_return
        ):
            raise subprocess.CalledProcessError(
                returncode=process.returncode,
                cmd=process.args,
                output=stdout,
                stderr=stderr,
            )
