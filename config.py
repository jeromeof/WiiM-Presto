# ==========================================================
# Configuration Module
# ==========================================================

# Import from secrets file
try:
    from secrets import WIFI_SSID, WIFI_PASSWORD, WIIM_IP, TIMEZONE_OFFSET
except ImportError:
    # Fallback defaults if secrets.py doesn't exist
    WIFI_SSID = "YOUR_WIFI_SSID"
    WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
    WIIM_IP = "192.168.31.139"
    TIMEZONE_OFFSET = 0

# Proxy configuration
PROXY_HOST = "192.168.31.1"
PROXY_PORT = 8081

# Timing configuration
POLL_INTERVAL_MS = 2000     # Polling interval in milliseconds
SOCKET_TIMEOUT_S = 5        # Socket timeout in seconds
HTTP_TIMEOUT = 6            # HTTP timeout in seconds

# Display configuration
BACKLIGHT_BRIGHTNESS = 0.25

# Debug mode
DEBUG = True
