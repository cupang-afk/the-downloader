"""Metadata retrieval utility functions."""

from collections.abc import Mapping
from contextlib import suppress

import requests


def get_total_size(
    session: requests.Session,
    url: str,
    headers: Mapping[str, str],
) -> int:
    """Retrieves the total size of a file from a URL using Content-Length header.

    Args:
        session: The requests session to use.
        url: The URL of the file.
        headers: Optional headers to include in the request.

    Returns:
        The total size in bytes, or -1 if it cannot be determined.
    """
    total: int = -1
    with suppress(requests.RequestException):
        # .get() with stream=True and only took the head
        # not all server support HEAD requests
        # but almost all server support GET requests
        res = session.get(url, headers=headers, stream=True, allow_redirects=True)
        res.raise_for_status()
        total = int(res.headers.get("Content-Length", total))
    return total
