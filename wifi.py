# ==========================================================
# WiFi Connection Module
# ==========================================================

import time
import network
try:
    import ntptime
except ImportError:
    ntptime = None
from config import WIFI_SSID, WIFI_PASSWORD, TIMEZONE_OFFSET
from utils import log

def connect_wifi():
    """
    Connect to WiFi using credentials from config.
    Raises RuntimeError if connection fails after 30 attempts.
    """
    log("Init WiFi")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(30):
            if wlan.isconnected():
                break
            time.sleep(0.5)

    if not wlan.isconnected():
        raise RuntimeError("WiFi failed")

    log("WiFi connected {}".format(wlan.ifconfig()[0]))

    # Synchronize time with NTP server
    if ntptime:
        try:
            log("Syncing time with NTP...")
            ntptime.settime()

            # Apply timezone offset if needed
            if TIMEZONE_OFFSET != 0:
                import machine
                rtc = machine.RTC()
                year, month, day, _, hour, minute, second, _ = rtc.datetime()

                # Adjust hour by timezone offset
                hour = (hour + TIMEZONE_OFFSET) % 24
                rtc.datetime((year, month, day, 0, hour, minute, second, 0))

                log("Time synced and adjusted for timezone offset: {}".format(TIMEZONE_OFFSET))
            else:
                log("Time synced with NTP (UTC)")
        except Exception as e:
            log("NTP sync failed: {}".format(e))
    else:
        log("ntptime module not available")
