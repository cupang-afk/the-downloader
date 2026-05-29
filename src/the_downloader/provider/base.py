"""Base classes and utilities for download providers.

This module provides the abstract base class for all download providers
and a mixin for providers that use subprocesses.
"""

import os
import subprocess
from abc import ABCMeta, abstractmethod
from collections.abc import Generator, Sequence
from contextlib import contextmanager, suppress
from logging import Logger
from pathlib import PurePath
from typing import Any, Literal, cast, final, overload

import certifi
import psutil

from ..types.protocol import CheckCanceled, UpdateProgress
from ..utils import logger

DEFAULT_CHUNK_SIZE: int = 1024 * 64  # 64 kb
DEFAULT_TIMEOUT: int = 10
DEFAULT_CA_CERT_PATH: str = certifi.where()


class BaseProvider(metaclass=ABCMeta):
    """Abstract base class for all download providers.

    All download providers should inherit from this class and implement
    the `download` method.
    """

    def __init__(
        self,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        timeout: int = DEFAULT_TIMEOUT,
        ca_cert_path: str = DEFAULT_CA_CERT_PATH,
    ) -> None:
        """Initialize the base provider.

        Args:
            chunk_size: The size of data chunks to read/write.
            timeout: The timeout in seconds for network operations.
            ca_cert_path: Path to the CA certificate bundle.
        """
        self._chunk_size: int = chunk_size
        self._timeout: int = timeout
        self._ca_cert_path: str = ca_cert_path

    @property
    def chunk_size(self) -> int:
        """Get the chunk size.

        Returns:
            The chunk size in bytes.
        """
        return self._chunk_size

    @property
    def timeout(self) -> int:
        """Get the timeout.

        Returns:
            The timeout in seconds.
        """
        return self._timeout

    @property
    def ca_cert_path(self) -> str:
        """Get the CA certificate path.

        Returns:
            Path to the CA certificate bundle.
        """
        return self._ca_cert_path

    # hook
    def __pre_hook__(self) -> None:
        """Hook called before the download starts."""
        return

    def __post_hook__(self) -> None:
        """Hook called after the download finishes."""
        return

    # method
    @final
    def get_logger(self) -> Logger:
        """Get the logger for this provider.

        Returns:
            A Logger instance named after the class.
        """
        return logger.get_logger(type(self).__name__)

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
        """Download a file from a URL to a destination.

        Args:
            url: The URL of the file to download.
            dest: The destination path.
            headers: HTTP headers to include in the request.
            check_canceled: A callback to check if the download should be canceled.
            update_progress: A callback to update the download progress.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError


class ProviderSubprocessMixin:
    """Mixin class for providers that use subprocesses.

    Provides utilities for running and terminating subprocesses.
    """

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
        """Run a subprocess and yield the Popen object.

        Args:
            command: The command to run as a sequence of strings.
            raise_non_zero_return: Whether to raise an exception if the process
                returns non-zero.
            terminate_timeout: The timeout in seconds to wait for the process
                to terminate.
            **kwargs: Additional arguments to pass to `subprocess.Popen`.

        Yields:
            A `subprocess.Popen` object.

        Raises:
            subprocess.CalledProcessError: If `raise_non_zero_return` is True
                and the process returns a non-zero exit code.
        """
        _logger: Logger = (
            logger.get_logger().getChild(type(self).__name__).getChild("popen_wrapper")
        )
        _logger.debug("Running: %s", command)

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
        _logger.debug("Started PID %d", process.pid)
        try:
            yield process
        finally:
            _logger.debug("Cleaning up PID %d", process.pid)
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
        """Terminate a process and its children.

        Args:
            process: The process to terminate.
            raise_nonzero_return: Whether to raise an exception if the process
                returns non-zero.
            terminate_timeout: The timeout in seconds to wait for each stage
                of termination.

        Raises:
            ValueError: If `terminate_timeout` is negative.
            subprocess.CalledProcessError: If `raise_nonzero_return` is True
                and the process returns a non-zero exit code.
        """
        _logger: Logger = (
            logger.get_logger()
            .getChild(type(self).__name__)
            .getChild("popen_terminate")
        )
        _logger.debug(
            "Terminating PID %d (timeout=%ds)", process.pid, terminate_timeout
        )

        if terminate_timeout < 0:
            raise ValueError("terminate_timeout must be >= 0")

        stdout: str | bytes | None = None
        stderr: str | bytes | None = None

        if process.poll() is None:
            _logger.debug("PID %d still running — terminating", process.pid)
            try:
                parent = psutil.Process(process.pid)
                processes = parent.children(recursive=True)
                processes.append(parent)
            except psutil.NoSuchProcess:
                _logger.debug("PID %d process tree vanished", process.pid)
                processes = []

            _logger.debug(
                "PID %d terminating %d process(es)", process.pid, len(processes)
            )
            for proc in processes:
                with suppress(psutil.NoSuchProcess):
                    proc.terminate()

            # cSpell: words  procs
            _, alive = psutil.wait_procs(processes, timeout=terminate_timeout)
            if alive:
                _logger.warning(
                    "PID %d — %d process(es) alive after terminate, killing",
                    process.pid,
                    len(alive),
                )

            for proc in alive:
                with suppress(psutil.NoSuchProcess):
                    proc.kill()

            psutil.wait_procs(alive, timeout=terminate_timeout)

        try:
            stdout, stderr = process.communicate(timeout=0)
        except subprocess.TimeoutExpired:
            _logger.exception("PID %d communicate timed out, killing", process.pid)
            process.kill()
            stdout, stderr = process.communicate()

        _logger.debug("PID %d exited with code %s", process.pid, process.returncode)

        if (
            process.returncode is not None
            and process.returncode != 0
            and raise_nonzero_return
        ):
            _logger.warning(
                "PID %d non-zero exit %s — raising", process.pid, process.returncode
            )
            raise subprocess.CalledProcessError(
                returncode=process.returncode,
                cmd=process.args,
                output=stdout,
                stderr=stderr,
            )
