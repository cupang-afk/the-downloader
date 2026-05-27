"""Custom exceptions for the downloader package."""


class DownloadError(Exception):
    """Base class for all download-related errors."""

    pass


class DownloadProviderError(DownloadError):
    """Raised when a download provider encounters an error."""

    pass


class RetryError(DownloadError):
    """Raised when a download fails after multiple retry attempts."""

    pass


class CallbackError(DownloadError):
    """Base class for all callback-related errors."""

    pass


class CallbackNonZeroReturnError(CallbackError):
    """Raised when a callback process returns a non-zero exit code."""

    pass
