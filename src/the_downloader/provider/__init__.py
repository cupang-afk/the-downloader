"""Provider module for download providers."""

from .aria2 import Aria2Downloader
from .base import DownloadProvider, SubprocessDownloaderMixin
from .curl import CurlDownloader
from .requests import RequestsDownloader
from .wget import WgetDownloader

__all__ = [
    "Aria2Downloader",
    "CurlDownloader",
    "DownloadProvider",
    "RequestsDownloader",
    "SubprocessDownloaderMixin",
    "WgetDownloader",
]
try:
    from .pycurl import PycurlDownloader  # noqa: F401

    __all__.append("PycurlDownloader")
except ImportError:
    pass
