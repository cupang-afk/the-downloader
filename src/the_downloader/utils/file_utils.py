import random
import shutil
import stat
import time
from os import PathLike
from pathlib import Path


def resolve_path(path: str | PathLike[str] | Path) -> Path:
    """Resolve a path-like object to a Path object.

    Args:
        path: Path-like object to resolve

    Returns:
        Resolved Path object
    """
    if isinstance(path, (str, PathLike)):
        path = Path(path)
    return path


def safe_delete(path: Path, max_retries: int = 10) -> None:
    """Safely delete a file or directory with retry logic.

    Args:
        path: Path to delete
        max_retries: Maximum number of retry attempts

    Raises:
        RuntimeError: If deletion fails after all retries
    """
    if not path.exists():
        return

    for attempt in range(max_retries):
        try:
            if path.is_dir():
                for item in path.rglob("*"):
                    if item.exists():
                        item.chmod(stat.S_IWRITE)
            path.chmod(stat.S_IWRITE)

            if path.is_file():
                path.unlink(missing_ok=True)
            else:
                shutil.rmtree(path)
            return

        except (PermissionError, OSError) as e:
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Failed to delete {path} after {max_retries} attempts"
                ) from e

            # Exponential backoff with jitter to avoid overwhelming the system
            # Base delay of 1 second, multiplied by 1.3^attempt with 10% random jitter
            wait_time = 1 * (1.3**attempt) * (1 + random.random() * 0.1)
            time.sleep(wait_time)


def remove_path_suffix(path: Path) -> tuple[str, list[str]]:
    """Remove suffixes from a path and return stem and suffixes separately.

    Args:
        path: Path to process

    Returns:
        Tuple of (stem, list of suffixes)
    """
    stem = path.stem.replace("".join(path.suffixes), "")
    suffixes = path.suffixes
    return stem, suffixes


def rename_path(
    path: Path,
    name_format: str = "{stem} ({number})",
) -> Path:
    """Rename a path to avoid conflicts by adding a number suffix.

    Args:
        path: Original path
        name_format: Format string for the new name

    Returns:
        New path that doesn't exist
    """
    if not path.exists():
        return path

    stem, suffixes = remove_path_suffix(path)

    number = 1
    while True:
        tmp = path.with_name(name_format.format(stem=stem, number=number)).with_suffix(
            "".join(suffixes)
        )
        if not tmp.exists():
            return tmp
        number += 1
