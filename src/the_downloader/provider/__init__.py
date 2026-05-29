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
    from warnings import warn

    warn(
        "pycurl not installed — PycurlProvider falling back to RequestsProvider",
        stacklevel=2,
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
