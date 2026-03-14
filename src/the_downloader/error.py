class DownloadError(Exception):
    """Represent a base exception for download-related errors."""

    pass


class CallbackError(DownloadError):
    """Represent an exception when a callback function encounters an error."""

    pass


class CallbackNonZeroReturnError(CallbackError):
    """Represent an exception when a callback returns a non-zero value."""

    pass


class ProviderError(DownloadError):
    """Represent an exception when a download provider encounters an error."""

    pass
