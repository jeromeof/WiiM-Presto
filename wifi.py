# ==========================================================
# WiFi Connection Module
# ==========================================================

import time
import network
from config import WIFI_SSID, WIFI_PASSWORD
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
