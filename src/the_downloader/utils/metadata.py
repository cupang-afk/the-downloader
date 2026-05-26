from collections.abc import Mapping
from contextlib import suppress

import requests


def get_total_size(
    session: requests.Session,
    url: str,
    headers: Mapping[str, str],
) -> int:
    total: int = -1
    with suppress(requests.RequestException):
        # .get() with stream=True and only took the head
        # not all server support HEAD requests
        # but almost all server support GET requests
        res = session.get(url, headers=headers, stream=True, allow_redirects=True)
        res.raise_for_status()
        total = int(res.headers.get("Content-Length", total))
    return total
