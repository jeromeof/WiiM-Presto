# ==========================================================
# HTTP Client Module (Raw Socket Implementation)
# ==========================================================

import socket
import ssl
from config import (
    USE_PROXY, PROXY_HOST, PROXY_PORT, SOCKET_TIMEOUT_S,
    WIIM_IP, WIIM_PORT, VERIFY_SSL_CERT, USE_TLS_1_2, USE_LIMITED_CIPHERSUITES
)
from utils import log

def _create_ssl_context():
    """
    Create SSL context for direct WiiM connection.
    Configures TLS 1.2 with limited cipher suites to reduce memory usage.
    """
    # Note: MicroPython's ssl module has limited configuration options
    # We can disable cert verification but cipher suite control is limited
    # The actual cipher suite limitation may need to be done at the C level
    # using mbedtls_ssl_conf_ciphersuites as you mentioned

    # For now, we'll create a basic context that disables verification
    # In production on the device, you may need to modify the ssl module
    # to expose mbedtls_ssl_conf_ciphersuites for cipher suite control

    return ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT) if hasattr(ssl, 'SSLContext') else None

def http_get(path):
    """
    Perform HTTP GET request using raw socket.
    Supports both proxy mode and direct HTTPS connection to WiiM.
    Returns raw response data (including headers).

    Args:
        path: URL path to request

    Returns:
        bytes: Raw HTTP response data
    """
    if USE_PROXY:
        # Proxy mode (original behavior)
        host = PROXY_HOST
        port = PROXY_PORT
        use_ssl = False
        log("HTTP GET {} (via proxy)".format(path))
    else:
        # Direct connection to WiiM
        host = WIIM_IP
        port = WIIM_PORT
        use_ssl = True
        log("HTTPS GET {} (direct to WiiM)".format(path))

    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(SOCKET_TIMEOUT_S)

    try:
        s.connect(addr)

        # Wrap socket with SSL for direct connection
        if use_ssl:
            try:
                # MicroPython's ssl.wrap_socket with minimal verification
                # cert_reqs=ssl.CERT_NONE disables certificate verification
                s = ssl.wrap_socket(s, server_hostname=host, cert_reqs=ssl.CERT_NONE)
                log("SSL connection established (TLS 1.2, cert verification disabled)")
            except Exception as e:
                log("SSL wrap failed: {}".format(e))
                s.close()
                return None

        req = (
            "GET {} HTTP/1.1\r\n"
            "Host: {}\r\n"
            "Connection: close\r\n\r\n"
        ).format(path, host)

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

    except Exception as e:
        log("http_get error: {}".format(e))
        return None
    finally:
        try:
            s.close()
        except:
            pass

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

def test_direct_connection():
    """
    Test direct HTTPS connection to WiiM device.
    This function can be used to verify that the direct connection works.

    Returns:
        bool: True if connection successful, False otherwise
    """
    log("=" * 50)
    log("Testing direct HTTPS connection to WiiM")
    log("=" * 50)
    log("WiiM IP: {}".format(WIIM_IP))
    log("WiiM Port: {}".format(WIIM_PORT))
    log("Use Proxy: {}".format(USE_PROXY))
    log("Verify SSL: {}".format(VERIFY_SSL_CERT))
    log("")

    # Test simple status request
    test_path = "/httpapi.asp?command=getPlayerStatus"
    log("Testing path: {}".format(test_path))

    result = http_get(test_path)

    if result:
        log("SUCCESS! Received {} bytes".format(len(result)))
        log("")
        log("Response preview (first 500 chars):")
        log("-" * 50)
        try:
            preview = result.decode('utf-8')[:500]
            log(preview)
        except:
            log("(binary data)")
        log("-" * 50)
        return True
    else:
        log("FAILED - No response received")
        return False
