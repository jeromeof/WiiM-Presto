# ==========================================================
# WiiM SSDP Discovery Module (MicroPython)
# Discovers WiiM/LinkPlay devices on the local network using
# SSDP/UPnP multicast (same protocol as the pywiim library,
# re-implemented for MicroPython raw sockets).
# ==========================================================

import socket
import time
import json
from utils import log

_SSDP_ADDR = "239.255.255.250"
_SSDP_PORT = 1900

# M-SEARCH request targeting MediaRenderer devices (standard LinkPlay target)
_MSEARCH = (
    "M-SEARCH * HTTP/1.1\r\n"
    "HOST: 239.255.255.250:1900\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 3\r\n"
    "ST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n"
    "\r\n"
)


def _parse_ip_from_ssdp(data):
    """Extract IP address from SSDP response LOCATION header."""
    try:
        text = data.decode("utf-8", "ignore")
        for line in text.split("\r\n"):
            if line.upper().startswith("LOCATION:"):
                url = line[9:].strip()
                # Parse IP from http://ip:port/path or http://ip/path
                if "://" in url:
                    rest = url.split("://", 1)[1]
                    host = rest.split("/")[0]
                    if ":" in host:
                        return host.split(":")[0]
                    return host
    except Exception as e:
        log("SSDP parse error: {}".format(e))
    return None


def _probe_wiim_http(ip, timeout=2):
    """
    Probe device via HTTP port 80 to confirm it's a WiiM/LinkPlay device
    and retrieve its name.

    Returns:
        str: Device name if confirmed WiiM, None otherwise
    """
    s = None
    try:
        addr = socket.getaddrinfo(ip, 80)[0][-1]
        s = socket.socket()
        s.settimeout(timeout)
        s.connect(addr)

        req = (
            "GET /httpapi.asp?command=getStatusEx HTTP/1.1\r\n"
            "Host: {}\r\n"
            "Connection: close\r\n\r\n"
        ).format(ip)
        s.send(req.encode())

        data = b""
        for _ in range(20):
            try:
                chunk = s.recv(512)
                if not chunk:
                    break
                data += chunk
                # Stop early once we have enough to check
                if len(data) > 200 and b"}" in data:
                    break
            except OSError:
                break

        if not data or b"DeviceName" not in data:
            return None

        # Extract JSON body
        start = data.find(b"{")
        if start < 0:
            return None
        body = data[start:]
        end = body.rfind(b"}")
        if end < 0:
            return None

        try:
            obj = json.loads(body[:end + 1])
            name = (
                obj.get("DeviceName")
                or obj.get("device_name")
                or obj.get("ssid")
                or ip
            )
            return str(name)
        except Exception:
            return ip  # Valid device but couldn't parse name

    except Exception as e:
        log("Probe {} error: {}".format(ip, e))
        return None
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass


def discover_wiim_devices(timeout=6):
    """
    Discover WiiM/LinkPlay devices on the local network via SSDP.

    Sends an M-SEARCH multicast, collects LOCATION responses, then
    validates each IP via a quick HTTP probe on port 80.

    Args:
        timeout: Seconds to wait for SSDP responses (default 6)

    Returns:
        list of dicts: [{"ip": "x.x.x.x", "name": "Device Name"}, ...]
    """
    log("SSDP discovery starting ({}s)...".format(timeout))
    seen_ips = []
    sock = None

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)  # Short recv timeout so we can check the deadline
        sock.bind(("", 0))

        sock.sendto(_MSEARCH.encode(), (_SSDP_ADDR, _SSDP_PORT))
        log("SSDP M-SEARCH sent")

        # Collect candidate IPs for `timeout` seconds
        deadline = time.ticks_ms() + timeout * 1000
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            try:
                data, _ = sock.recvfrom(1024)
                ip = _parse_ip_from_ssdp(data)
                if ip and ip not in seen_ips:
                    seen_ips.append(ip)
                    log("SSDP candidate: {}".format(ip))
            except OSError:
                pass  # recv timed out, keep waiting

    except Exception as e:
        log("SSDP error: {}".format(e))
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass

    log("SSDP found {} candidate(s), probing...".format(len(seen_ips)))

    # Validate each candidate via HTTP
    devices = []
    for ip in seen_ips:
        name = _probe_wiim_http(ip)
        if name is not None:
            log("Confirmed WiiM: {} @ {}".format(name, ip))
            devices.append({"ip": ip, "name": name})

    log("Discovery complete: {} WiiM device(s) found".format(len(devices)))
    return devices
