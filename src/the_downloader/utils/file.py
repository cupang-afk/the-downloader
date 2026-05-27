"""File management utility functions."""

import shutil
import stat
from pathlib import Path

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
    binary_path: Path = Path(path)
    if binary_path.is_absolute():
        if not binary_path.is_file():
            raise FileNotFoundError(
                f"Binary not found at {binary_path} or is not a file/exists"
            )
        return binary_path.absolute()
    else:
        bin_from_path: str | None = shutil.which(binary_path.name)
        if not bin_from_path:
            raise FileNotFoundError(f"Binary {binary_path.name} not found in PATH")
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
    path = Path(path)
    if not path.exists():
        return

    @retry(
        max_retries=max_retries,
        delay=retry_delay,
        backoff_factor=retry_backoff_factor,
    )
    def handler() -> None:
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
