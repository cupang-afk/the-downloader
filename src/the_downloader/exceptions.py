class DownloadError(Exception):
    pass


class DownloadProviderError(DownloadError):
    pass


class RetryError(DownloadError):
    pass


class CallbackError(DownloadError):
    pass


class CallbackNonZeroReturnError(CallbackError):
    pass
