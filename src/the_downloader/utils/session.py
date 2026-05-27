"""Requests session utility functions."""

from functools import cache

import requests


@cache
def get_requests_session() -> requests.Session:
    """Returns a cached requests session instance.

    Returns:
        A cached requests.Session object.
    """
    return requests.Session()
