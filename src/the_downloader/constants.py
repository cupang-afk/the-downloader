"""Constants for the downloader.

This module contains default configurations and constants used across the package.
"""

import json
import os
import warnings
from pathlib import Path
from types import MappingProxyType
from typing import Any

import certifi

from .__version__ import __version__

ENV_PREFIX = "DL_"


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        warnings.warn(
            f"Invalid integer in {key}: {val!r}, using default {default}",
            stacklevel=2,
        )
        return default


def _env_path(key: str, default: str) -> str:
    val = os.environ.get(key)
    if val is None:
        return default
    if not Path(val).is_file():
        warnings.warn(
            f"File not found in {key}: {val!r}, using default {default!r}",
            stacklevel=2,
        )
        return default
    return val


def _env_json(key: str, default: dict[str, str]) -> dict[str, str]:
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        parsed: dict[str, Any] = json.loads(val)
        for k, v in parsed.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ValueError("all keys and values must be strings")
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        warnings.warn(
            f"Invalid JSON in {key}: {e}, ignoring",
            stacklevel=2,
        )
        return default


DEFAULT_HEADERS = MappingProxyType(
    {
        "User-Agent": f"TheDownloader/{__version__}",
        **_env_json(f"{ENV_PREFIX}HEADERS", {}),
    }
)

DEFAULT_CHUNK_SIZE = _env_int(f"{ENV_PREFIX}CHUNK_SIZE", 1024 * 64)

DEFAULT_TIMEOUT = _env_int(f"{ENV_PREFIX}TIMEOUT", 30)

DEFAULT_MAX_RETRIES = _env_int(f"{ENV_PREFIX}MAX_RETRIES", 3)

DEFAULT_RETRY_DELAY = _env_int(f"{ENV_PREFIX}RETRY_DELAY", 1)

DEFAULT_RETRY_BACKOFF_FACTOR = 2.0

DEFAULT_CA_CERT_PATH = str(
    Path(_env_path(f"{ENV_PREFIX}CA_CERT_PATH", certifi.where())).absolute()
)
