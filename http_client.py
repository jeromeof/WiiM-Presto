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
        # Parse URL - handle both http://host/path and http://host:port/path
        parts = url.split("/", 3)
        host_port = parts[2]  # host or host:port
        path = "/" + parts[3] if len(parts) > 3 else "/"

        # Extract host and port
        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            port = int(port_str)
        else:
            host = host_port
            port = 80

        log("Fetching from {}:{} path {}".format(host, port, path[:50]))
        addr = socket.getaddrinfo(host, port)[0][-1]

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
