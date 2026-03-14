"""Downloader module for downloading files with progress tracking."""

from .callback import DefaultDownloadCallback, DownloadCallback
from .downloader import Downloader, QueueDownloader
from .error import DownloadError, ProviderError
from .provider.base import DownloadProvider, SubprocessDownloaderMixin
from .task import DownloadTask, DownloadTaskStatus

__all__ = [
    "DefaultDownloadCallback",
    "DownloadCallback",
    "DownloadError",
    "DownloadProvider",
    "DownloadTask",
    "DownloadTaskStatus",
    "Downloader",
    "ProviderError",
    "QueueDownloader",
    "SubprocessDownloaderMixin",
]
