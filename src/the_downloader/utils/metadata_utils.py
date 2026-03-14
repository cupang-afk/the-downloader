from collections.abc import Mapping

import requests


def get_total_size(
    session: requests.Session, url: str, headers: Mapping[str, str]
) -> int:
    """Get the total size of a file from HTTP response headers.

    Args:
        session: HTTP session to use for the request
        url: URL to check for file size
        headers: HTTP headers to include in the request

    Returns:
        Total file size in bytes, or -1 if unknown
    """
    total: int = -1
    try:
        with session.head(
            url,
            headers=headers,
            allow_redirects=True,
            timeout=10,
        ) as res:
            res.raise_for_status()
            length = res.headers.get("Content-Length", 0)
            total = int(length)
            if total != 0:
                return total
    except requests.RequestException:
        pass

    try:
        with session.get(
            url,
            headers=headers,
            stream=True,
            allow_redirects=True,
            timeout=10,
        ) as res:
            res.raise_for_status()
            length = res.headers.get("Content-Length", 0)
            total = int(length)
    except requests.RequestException:
        pass

    return total
