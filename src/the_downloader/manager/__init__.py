"""Download manager implementations.

This package provides different download manager classes for handling downloads
sequentially or in parallel using a thread pool.
"""

from .base import BaseManager
from .basic import BasicDownloadManager
from .queue import QueueDownloadManager

__all__ = [
    "BaseManager",
    "BasicDownloadManager",
    "QueueDownloadManager",
]
