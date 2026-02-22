"""Utility functions for file and path operations."""

import random
import shutil
import stat
import time
from pathlib import Path


def ensure_path(path: str | Path) -> Path:
    """Ensures the input is converted to a Path object.

    Args:
        path: A string or Path object.

    Returns:
        A Path object.
    """
    if isinstance(path, str):
        path = Path(path)
    return path


def safe_delete(path: Path, max_retries: int = 10) -> None:
    """Safely deletes a file or directory with retries and permission handling.

    This function handles permission errors by retrying with exponential backoff
    and ensures files are writable before deletion.

    Args:
        path: The path to delete.
        max_retries: Maximum number of deletion attempts. Defaults to 10.

    Raises:
        RuntimeError: If deletion fails after all retries.
    """
    if not path.exists():
        return

    for attempt in range(max_retries):
        try:
            # Make writable before deletion
            if path.is_dir():
                for item in path.rglob("*"):
                    if item.exists():
                        item.chmod(stat.S_IWRITE)
            path.chmod(stat.S_IWRITE)

            # Delete
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

            wait_time = 1 * (1.3**attempt) * (1 + random.random() * 0.1)
            time.sleep(wait_time)


def remove_path_suffix(path: Path) -> tuple[str, list[str]]:
    """Removes all suffixes from a path and returns the stem and suffixes.

    Args:
        path: The path to process.

    Returns:
        A tuple of (stem without suffixes, list of suffixes).
    """
    stem = path.stem.replace("".join(path.suffixes), "")
    suffixes = path.suffixes
    return stem, suffixes


def rename_path(
    path: Path,
    name_format: str = "{stem} ({number})",
) -> Path:
    """Generates a new unique path by appending a number if the path exists.

    Args:
        path: The original path.
        name_format: Format string for the new name. Must contain {stem} and
            {number} placeholders. Defaults to "{stem} ({number})".

    Returns:
        A new unique path that doesn't exist.
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
