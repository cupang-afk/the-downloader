import shutil
import stat
from pathlib import Path

from ..constants import DEFAULT_MAX_RETRIES, DEFAULT_RETRY_DELAY
from .retry import retry


def resolve_binary(path: str | Path) -> Path:
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
    max_retries: int = DEFAULT_MAX_RETRIES,
    delay: int = DEFAULT_RETRY_DELAY,
):
    path = Path(path)
    if not path.exists():
        return

    @retry(max_retries=max_retries, delay=delay)
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
