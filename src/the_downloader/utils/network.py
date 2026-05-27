"""Network utility functions."""

import socket


def check_open_port(port: int, host: str = "") -> bool:
    """Checks if a port is available on the specified host.

    Args:
        port: The port number to check.
        host: The host to check on. Defaults to empty string (all interfaces).

    Returns:
        True if the port is available, False otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
        else:
            return True
