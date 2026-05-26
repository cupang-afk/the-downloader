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
        "pycurl is not installed, PycurlProvider will not be available, fallback to RequestsProvider"
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
