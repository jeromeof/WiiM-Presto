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

    import rp2
    rp2.country('GB')  # Set country code for correct channel scanning

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # Disable power management to improve stability on Pico W / CYW43
    # 0xa11140 is the value for "performance" mode (disables power saving)
    try:
        wlan.config(pm=0xa11140)
        log("WiFi power management disabled (performance mode)")
    except Exception as e:
        log("Failed to set WiFi PM: {}".format(e))
        
    log("WLAN interface activated")

    # Scan for networks (helps debug if SSID not found)
    try:
        log("Scanning for networks...")
        networks = wlan.scan()
        log("Found {} networks".format(len(networks)))
        ssid_found = False
        found_ssids = []
        for net in networks:
            try:
                ssid = net[0].decode('utf-8')
                if ssid:
                    found_ssids.append(ssid)
                if ssid == WIFI_SSID:
                    ssid_found = True
            except Exception:
                pass
        if ssid_found:
            log("Target SSID found: {}".format(WIFI_SSID))
        else:
            log("WARNING: SSID '{}' not found in scan!".format(WIFI_SSID))
            log("Networks visible: {}".format(found_ssids))
    except Exception as e:
        log("Network scan failed: {}".format(e))

    if not wlan.isconnected():
        log("Attempting connection...")

        # Try connecting up to 3 times with full reset between attempts
        max_retries = 3
        for retry in range(max_retries):
            log("=== Connection attempt {} of {} ===".format(retry + 1, max_retries))

            if retry > 0:
                log("Performing deep WiFi reset...")
                try:
                    wlan.disconnect()
                    wlan.active(False)
                    time.sleep(2)  # Increased delay
                
                    # Re-create the WLAN object - sometimes helps with stuck driver
                    wlan = network.WLAN(network.STA_IF)
                    wlan.active(True)
                    
                    # Ensure PM is disabled after reset
                    try:
                        wlan.config(pm=0xa11140)
                    except:
                        pass
                        
                    time.sleep(2)  # Increased delay
                    log("WiFi interface re-initialized")
                except Exception as e:
                    log("Reset error: {}".format(e))

            log("Calling wlan.connect()...")
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
            # Wait up to 30 seconds for this attempt
            consecutive_nonet = 0
            for i in range(30):
                status = wlan.status()

                # Only log every 5 attempts to reduce spam
                if i % 5 == 0 or status != 1:
                    log("Attempt {}/30, status: {}".format(i+1, status))

                if wlan.isconnected():
                    log("Connection successful!")
                    break

                # Status codes (CYW43 on Pico W / Presto):
                #  3 = CYW43_LINK_UP (Connected)
                #  0 = CYW43_LINK_DOWN (Disconnected)
                #  1 = CYW43_LINK_JOIN (Connecting)
                #  2 = CYW43_LINK_NOIP (Connected, waiting for IP)
                # -1 = CYW43_LINK_FAIL (Failed)
                # -2 = CYW43_LINK_NONET (Network not found)
                # -3 = CYW43_LINK_BADAUTH (Wrong password)

                if status == -3:
                    log("ERROR: Wrong password! (status: -3)")
                    raise RuntimeError("Wrong WiFi password")
            
                if status == -2:
                    consecutive_nonet += 1
                    # If we get NONET multiple times in a row, then break and try full reset
                    if consecutive_nonet >= 3:
                        log("ERROR: Network not found persistently (status: -2)")
                        break
                else:
                    consecutive_nonet = 0

                if status < 0 and status not in (-1, -2): 
                    log("WiFi error: status {}".format(status))
                    break

                time.sleep(1.0)

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

    sync_ntp()


def sync_ntp():
    """
    Synchronize time with NTP and apply timezone offset.
    Safe to call at any time while WiFi is connected.
    Returns True on success, False on failure.
    """
    if ntptime is None:
        log("ntptime module not available")
        return False
    try:
        log("Syncing time with NTP...")
        ntptime.settime()

        if TIMEZONE_OFFSET != 0:
            import machine
            rtc = machine.RTC()
            year, month, day, _, hour, minute, second, _ = rtc.datetime()
            hour = (hour + TIMEZONE_OFFSET) % 24
            rtc.datetime((year, month, day, 0, hour, minute, second, 0))
            log("NTP synced, TZ offset: {}h".format(TIMEZONE_OFFSET))
        else:
            log("NTP synced (UTC)")
        return True
    except Exception as e:
        log("NTP sync failed: {}".format(e))
        return False
