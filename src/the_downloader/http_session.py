import requests
from requests.adapters import HTTPAdapter
from requests.cookies import RequestsCookieJar

from .constants import CA_CERT_PATH, DEFAULT_HEADERS

adapter = HTTPAdapter(
    pool_connections=100,
    pool_maxsize=100,
    pool_block=True,
)


def get_session():
    """Return a configured HTTP session for download operations.

    Returns:
        Configured requests.Session with connection pooling,
        certificate verification, and default headers
    """
    session = requests.Session()

    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.verify = CA_CERT_PATH
    session.headers.update(DEFAULT_HEADERS)
    session.cookies = RequestsCookieJar()

    return session
