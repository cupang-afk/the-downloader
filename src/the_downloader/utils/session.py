import requests

_session: requests.Session | None = None


def get_requests_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
    return _session
