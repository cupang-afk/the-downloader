"""Core components of the-downloader.

This module provides the main classes for managing downloads, including various
download managers and tasks.
"""

from .callback import BasicDownloadCallback
from .manager import BasicDownloadManager, QueueDownloadManager
from .task import DownloadTask

__all__ = [
    "BasicDownloadCallback",
    "BasicDownloadManager",
    "DownloadTask",
    "QueueDownloadManager",
]
