"""File management utility functions."""

import shutil
import stat
from logging import Logger
from pathlib import Path

from . import logger
from .retry import retry


def resolve_binary(path: str | Path) -> Path:
    """Resolves a binary path to its absolute path.

    Args:
        path: The path to the binary, either absolute or a name in PATH.

    Returns:
        The absolute path to the binary.

    Raises:
        FileNotFoundError: If the binary cannot be found.
    """
    _logger: Logger = logger.get_logger().getChild("resolve_binary")
    binary_path: Path = Path(path)
    if binary_path.is_absolute():
        if not binary_path.is_file():
            _logger.error("Binary not found at %s", binary_path)
            raise FileNotFoundError(
                f"Binary not found at {binary_path} or is not a file/exists"
            )
        _logger.debug("Resolved %s", binary_path.absolute())
        return binary_path.absolute()
    else:
        bin_from_path: str | None = shutil.which(binary_path.name)
        if not bin_from_path:
            _logger.error("Binary %s not found in PATH", binary_path.name)
            raise FileNotFoundError(f"Binary {binary_path.name} not found in PATH")
        _logger.debug("Resolved %s \u2192 %s", binary_path.name, bin_from_path)
        return Path(bin_from_path).absolute()


def delete(
    path: str | Path,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    retry_backoff_factor: float = 2.0,
) -> None:
    """Deletes a file or directory with retry logic and permission handling.

    Args:
        path: The path to the file or directory to delete.
        max_retries: Maximum number of delete attempts.
        retry_delay: Initial delay between retries in seconds.
        retry_backoff_factor: Factor to increase the delay between retries.
    """
    _logger: Logger = logger.get_logger().getChild("delete")
    path = Path(path)
    if not path.exists():
        return

    _logger.debug("Deleting %s", path)

    @retry(
        max_retries=max_retries,
        delay=retry_delay,
        backoff_factor=retry_backoff_factor,
    )
    def handler() -> None:
        """Delete the path once with permission handling."""
        if path.is_dir():
            for item in path.rglob("*"):
                if item.exists():
                    item.chmod(stat.S_IWRITE)

        path.chmod(stat.S_IWRITE)
        if path.is_file():
            path.unlink(missing_ok=True)
        else:
            shutil.rmtree(path)

    handler()
    _logger.debug("Deleted %s", path)
