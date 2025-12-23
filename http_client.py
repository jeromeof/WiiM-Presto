# ==========================================================
# HTTP Client Module (Raw Socket Implementation)
# ==========================================================

import socket
from config import PROXY_HOST, PROXY_PORT, SOCKET_TIMEOUT_S
from utils import log

def http_get(path):
    """
    Perform HTTP GET request using raw socket.
    Returns raw response data (including headers).

    Args:
        path: URL path to request

    Returns:
        bytes: Raw HTTP response data
    """
    addr = socket.getaddrinfo(PROXY_HOST, PROXY_PORT)[0][-1]
    s = socket.socket()
    s.settimeout(SOCKET_TIMEOUT_S)

    try:
        s.connect(addr)

        req = (
            "GET {} HTTP/1.1\r\n"
            "Host: {}\r\n"
            "Connection: close\r\n\r\n"
        ).format(path, PROXY_HOST)

        log("HTTP GET {}".format(path))
        s.send(req.encode())

        data = b""
        while True:
            try:
                chunk = s.recv(1024)
                if not chunk:
                    break
                data += chunk
            except OSError:
                break

        return data

    finally:
        s.close()

def fetch_url(url, timeout=5):
    """
    Fetch content from arbitrary URL using raw socket.
    Used for downloading album art.

    Args:
        url: Full URL to fetch
        timeout: Socket timeout in seconds

    Returns:
        bytes: Response body (headers stripped) or None on error
    """
    try:
        # Parse URL
        host, path = url.split("/", 3)[2], "/" + url.split("/", 3)[3]
        addr = socket.getaddrinfo(host, 80)[0][-1]

        s = socket.socket()
        s.settimeout(timeout)
        s.connect(addr)

        s.send(
            "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n"
            .format(path, host).encode()
        )

        data = b""
        while True:
            chunk = s.recv(1024)
            if not chunk:
                break
            data += chunk

        s.close()

        # Strip HTTP headers
        sep = data.find(b"\r\n\r\n")
        if sep < 0:
            log("fetch_url: no HTTP body")
            return None

        return data[sep + 4:]

    except Exception as e:
        log("fetch_url error: {}".format(e))
        return None
