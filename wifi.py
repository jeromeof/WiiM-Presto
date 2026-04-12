# ==========================================================
# WiFi Connection Module
# ==========================================================

import time
import network
try:
    import ntptime
except ImportError:
    ntptime = None
from config import WIFI_SSID, WIFI_PASSWORD, TIMEZONE_OFFSET, DST_RULE
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


def _day_of_week(year, month, day):
    """Return day of week using Tomohiko Sakamoto's algorithm. 0=Sunday, 6=Saturday."""
    t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
    if month < 3:
        year -= 1
    return (year + year // 4 - year // 100 + year // 400 + t[month - 1] + day) % 7


def _last_sunday(year, month):
    """Return the day-of-month of the last Sunday in the given month."""
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        last_day = 29
    else:
        last_day = days_in_month[month - 1]
    dow = _day_of_week(year, month, last_day)  # 0=Sun
    return last_day - dow


def _nth_sunday(year, month, n):
    """Return the day-of-month of the nth Sunday (1-based) in the given month."""
    dow = _day_of_week(year, month, 1)  # weekday of 1st: 0=Sun
    first_sunday = 1 + (7 - dow) % 7
    return first_sunday + (n - 1) * 7


def _eu_dst_offset(year, month, day, hour):
    """
    Return DST offset (0 or 1) for EU/Ireland/UK rules.
    DST starts: last Sunday of March at 01:00 UTC    → +1h
    DST ends:   last Sunday of October at 01:00 UTC  → +0h
    """
    now = (month, day, hour)
    dst_start = (3, _last_sunday(year, 3), 1)
    dst_end   = (10, _last_sunday(year, 10), 1)
    return 1 if dst_start <= now < dst_end else 0


def _us_dst_offset(year, month, day, hour, base_offset):
    """
    Return DST offset (0 or 1) for US/Canada rules (since 2007).
    DST starts: 2nd Sunday of March at 02:00 local standard time
    DST ends:   1st Sunday of November at 02:00 local standard time
    Transition hour is converted to UTC using base_offset.
    """
    utc_hour = (2 - base_offset) % 24
    now = (month, day, hour)
    dst_start = (3, _nth_sunday(year, 3, 2), utc_hour)
    dst_end   = (11, _nth_sunday(year, 11, 1), utc_hour)
    return 1 if dst_start <= now < dst_end else 0


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

        import machine
        rtc = machine.RTC()
        year, month, day, _, hour, minute, second, _ = rtc.datetime()

        if DST_RULE == "EU":
            dst_offset = _eu_dst_offset(year, month, day, hour)
        elif DST_RULE == "US":
            dst_offset = _us_dst_offset(year, month, day, hour, TIMEZONE_OFFSET)
        else:
            dst_offset = 0
        total_offset = TIMEZONE_OFFSET + dst_offset

        if total_offset != 0:
            hour = (hour + total_offset) % 24
            rtc.datetime((year, month, day, 0, hour, minute, second, 0))

        log("NTP synced, UTC+{} (base:{}, DST:{})".format(total_offset, TIMEZONE_OFFSET, dst_offset))
        return True
    except Exception as e:
        log("NTP sync failed: {}".format(e))
        return False
