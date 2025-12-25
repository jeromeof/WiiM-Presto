# ==========================================================
# Configuration Module
# ==========================================================

# Import from secrets file
try:
    from secrets import (
        WIFI_SSID, WIFI_PASSWORD, WIIM_IP, TIMEZONE_OFFSET,
        USE_ROON, ROON_PROXY_IP, ROON_PROXY_PORT, ROON_ZONE_ID
    )
except ImportError:
    # Fallback defaults if secrets.py doesn't exist
    WIFI_SSID = "YOUR_WIFI_SSID"
    WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
    WIIM_IP = "192.168.31.139"
    TIMEZONE_OFFSET = 0
    # Roon settings
    USE_ROON = False  # Set to True to use Roon instead of WiiM
    ROON_PROXY_IP = "192.168.1.100"
    ROON_PROXY_PORT = 9876
    ROON_ZONE_ID = None  # None = auto-detect first zone

# Proxy configuration
USE_PROXY = False  # Set to True to use proxy, False for direct connection
PROXY_HOST = "192.168.31.1"  # Router IP (only used if USE_PROXY=True)
PROXY_PORT = 8081

# Direct connection SSL/TLS configuration (for direct WiiM connection)
WIIM_PORT = 443  # HTTPS port for direct connection
USE_TLS_1_2 = True  # Force TLS 1.2 (reduces memory requirements)
VERIFY_SSL_CERT = False  # Disable certificate verification for WiiM devices
USE_LIMITED_CIPHERSUITES = True  # Use only AES-128-GCM to reduce memory

# Timing configuration
POLL_INTERVAL_SLOW_MS = 10000   # Slow polling: 10 seconds (during track playback)
POLL_INTERVAL_FAST_MS = 1000    # Fast polling: 1 second (near end of track)
TRACK_END_THRESHOLD_S = 5       # Start fast polling when < 5 seconds remaining
SOCKET_TIMEOUT_S = 2.5          # Socket timeout in seconds (short for responsiveness)
HTTP_TIMEOUT = 3                # HTTP timeout in seconds

# Display configuration
BACKLIGHT_BRIGHTNESS = 0.25

# Weather configuration (OpenWeatherMap)
WEATHER_API_KEY = "d98a842ad69d559cd854f8b6a19108b0"
WEATHER_LOCATION = "Dublin,IE"
WEATHER_UNITS = "metric"  # metric or imperial
WEATHER_CACHE_TIME = 3600  # 1 hour in seconds

# Touch input configuration
BUTTON_TIMEOUT_MS = 5000  # 5 seconds until buttons auto-hide
CONTROL_COMMAND_DELAY_MS = 500  # Delay after control command for state propagation

# Preset configuration
# Labels for the 4 preset buttons shown on clock screen
# Set to None to disable a preset button
PRESET_LABELS = [
    "Jazz",      # Preset 1
    "Classical", # Preset 2
    "Rock",      # Preset 3
    "Chill"      # Preset 4
]

# Debug mode
DEBUG = True
