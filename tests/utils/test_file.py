"""Tests for file utility behavior."""

from pathlib import Path

import pytest

from the_downloader.utils.file import delete, resolve_binary


def test_delete_missing_path(tmp_path: Path) -> None:
    """Ignore a path that does not exist."""
    missing_path = tmp_path / "missing.txt"

    delete(missing_path)

    assert not missing_path.exists()


def test_delete_file(tmp_path: Path) -> None:
    """Delete an existing file path."""
    file_path = tmp_path / "target.txt"
    file_path.write_text("content", encoding="utf-8")

    delete(file_path)

    assert not file_path.exists()


def test_delete_directory(tmp_path: Path) -> None:
    """Delete an existing directory path recursively."""
    directory_path = tmp_path / "target"
    nested_path = directory_path / "nested" / "file.txt"
    nested_path.parent.mkdir(parents=True)
    nested_path.write_text("content", encoding="utf-8")

    delete(directory_path)

    assert not directory_path.exists()


def test_delete_read_only_file(tmp_path: Path) -> None:
    """Delete a read-only file by making it writable first."""
    file_path = tmp_path / "readonly.txt"
    file_path.write_text("content", encoding="utf-8")
    file_path.chmod(0o400)

    delete(file_path)

    assert not file_path.exists()


def test_delete_rejects_invalid_type() -> None:
    """Reject input that is not string-like or path-like."""
    with pytest.raises(TypeError):
        delete(123)  # pyright: ignore[reportArgumentType]


def test_resolve_binary_absolute_file(tmp_path: Path) -> None:
    """Resolve an existing absolute file path."""
    binary_path = tmp_path / "tool.exe"
    binary_path.touch()

    result = resolve_binary(binary_path)

    assert result == binary_path.absolute()


def test_resolve_binary_absolute_missing(tmp_path: Path) -> None:
    """Reject a missing absolute file path."""
    binary_path = tmp_path / "missing.exe"

    with pytest.raises(FileNotFoundError):
        resolve_binary(binary_path)


def test_resolve_binary_path_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve a binary name through PATH lookup."""
    expected_path = Path("/usr/bin/tool")

    def fake_which(name: str) -> str | None:
        """Return a matching path for the expected binary name."""
        if name == "tool":
            return str(expected_path)
        return None

    monkeypatch.setattr("the_downloader.utils.file.shutil.which", fake_which)

    result = resolve_binary("tool")

    assert result == expected_path.absolute()


def test_resolve_binary_path_lookup_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a binary name missing from PATH lookup."""

    def fake_which(name: str) -> str | None:
        """Return no match for any binary name."""
        assert name == "missing-tool"
        return None

    monkeypatch.setattr("the_downloader.utils.file.shutil.which", fake_which)

    with pytest.raises(FileNotFoundError):
        resolve_binary("missing-tool")


def test_resolve_binary_rejects_invalid_type() -> None:
    """Reject input that is not string-like or path-like."""
    with pytest.raises(TypeError):
        resolve_binary(123)  # pyright: ignore[reportArgumentType]
