"""Download providers package.

This package contains various download provider implementations such as
Aria2, Curl, Requests, Wget, and Pycurl.
"""

from .aria2 import Aria2Provider
from .base import BaseProvider
from .curl import CurlProvider
from .requests import RequestsProvider
from .wget import WgetProvider

try:
    from .pycurl import PycurlProvider
except ImportError:
    from ..logger import logger

    logger.warning(
        "pycurl is not installed, PycurlProvider will not be available, "
        + "fallback PycurlProvider to use RequestsProvider"
    )
    PycurlProvider = RequestsProvider

__all__ = [
    "Aria2Provider",
    "BaseProvider",
    "CurlProvider",
    "PycurlProvider",
    "RequestsProvider",
    "WgetProvider",
]
