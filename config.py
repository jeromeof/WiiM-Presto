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
POLL_INTERVAL_SLOW_MS = 10000   # Slow polling: 10 seconds (during track playback)
POLL_INTERVAL_FAST_MS = 1000    # Fast polling: 1 second (near end of track)
TRACK_END_THRESHOLD_S = 30      # Start fast polling when < 30 seconds remaining
SOCKET_TIMEOUT_S = 5            # Socket timeout in seconds
HTTP_TIMEOUT = 6                # HTTP timeout in seconds

# Display configuration
BACKLIGHT_BRIGHTNESS = 0.25

# Weather configuration (OpenWeatherMap)
WEATHER_API_KEY = "d98a842ad69d559cd854f8b6a19108b0"
WEATHER_LOCATION = "Dublin,IE"
WEATHER_UNITS = "metric"  # metric or imperial
WEATHER_CACHE_TIME = 1800  # 30 minutes in seconds

# Debug mode
DEBUG = True
