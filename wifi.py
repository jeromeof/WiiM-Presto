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
    log("Connecting to SSID: {}".format(WIFI_SSID))

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    log("WLAN interface activated")

    # Scan for networks (helps debug if SSID not found)
    try:
        log("Scanning for networks...")
        networks = wlan.scan()
        log("Found {} networks".format(len(networks)))
        ssid_found = False
        for net in networks:
            ssid = net[0].decode('utf-8')
            if ssid == WIFI_SSID:
                ssid_found = True
                log("Target SSID found: {}".format(WIFI_SSID))
                break
        if not ssid_found:
            log("WARNING: SSID '{}' not found in scan!".format(WIFI_SSID))
    except Exception as e:
        log("Network scan failed: {}".format(e))

    if not wlan.isconnected():
        log("Attempting connection...")

        # Try connecting up to 3 times with full reset between attempts
        max_retries = 3
        for retry in range(max_retries):
            log("=== Connection attempt {} of {} ===".format(retry + 1, max_retries))

            if retry > 0:
                log("Performing WiFi reset...")
                # Disconnect and reset between retries
                try:
                    wlan.disconnect()
                    log("Disconnected")
                except Exception as e:
                    log("Disconnect error: {}".format(e))

                time.sleep(1)
                wlan.active(False)
                log("WiFi deactivated")
                time.sleep(1)
                wlan.active(True)
                log("WiFi reactivated")
                time.sleep(1)

            log("Calling wlan.connect()...")
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            log("Connection initiated, waiting for status...")

            # Wait up to 15 seconds for this attempt
            for i in range(30):
                status = wlan.status()

                # Only log every 5 attempts to reduce spam
                if i % 5 == 0 or status != 1:
                    log("Attempt {}/30, status: {}".format(i+1, status))

                if wlan.isconnected():
                    log("Connection successful!")
                    break

                # Status codes:
                # -1 = Error/connection lost
                # 0 = STAT_IDLE
                # 1 = STAT_CONNECTING
                # 2 = STAT_WRONG_PASSWORD
                # 3 = STAT_NO_AP_FOUND
                # 4 = STAT_CONNECT_FAIL
                # 5 = STAT_GOT_IP (but should be connected by now)

                if status == -1:
                    log("Status -1: Connection error, breaking to retry...")
                    break  # Break inner loop to retry
                elif status == 2:
                    log("ERROR: Wrong password!")
                    raise RuntimeError("Wrong WiFi password")
                elif status == 3:
                    log("ERROR: Network not found!")
                    raise RuntimeError("WiFi network '{}' not found".format(WIFI_SSID))
                elif status == 4:
                    log("ERROR: Connection failed!")
                    break  # Try again

                time.sleep(0.5)

            # Check if we succeeded after inner loop
            if wlan.isconnected():
                log("Connected! Breaking retry loop.")
                break
            else:
                log("Not connected after attempt. Status: {}".format(wlan.status()))

        # Final check after all retries
        log("Exited retry loop. Connected: {}".format(wlan.isconnected()))
        if not wlan.isconnected():
            log("All {} retry attempts exhausted".format(max_retries))

    if not wlan.isconnected():
        status = wlan.status()
        log("Final status: {}".format(status))
        raise RuntimeError("WiFi timeout (status: {})".format(status))

    ip = wlan.ifconfig()[0]
    log("WiFi connected! IP: {}".format(ip))

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
