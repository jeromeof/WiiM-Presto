# ==========================================================
# WiiM Now Playing / Clock for Pimoroni Presto (MicroPython)
# ==========================================================

import gc
import uasyncio as asyncio
from config import POLL_INTERVAL_SLOW_MS, POLL_INTERVAL_FAST_MS, TRACK_END_THRESHOLD_S
from utils import log, hex_to_text
from wifi import connect_wifi
from wiim_client import fetch_player_status, fetch_meta_info
from display_manager import draw_clock, draw_track

# =======================
# MAIN MONITOR LOOP
# =======================

async def monitor():
    """
    Main monitoring loop that polls WiiM device status and updates display.
    Shows clock when stopped, track info with album art when playing.
    Uses smart polling: slow during track, fast near end.
    """
    log("Enter monitor loop")

    last_state = None
    last_track_id = None
    last_art_url = None  # Track if we successfully got album art

    while True:
        gc.collect()

        # Fetch player status
        status = fetch_player_status()
        if not status:
            if last_state != "clock":
                draw_clock()
                last_state = "clock"
            await asyncio.sleep_ms(POLL_INTERVAL_SLOW_MS)
            continue

        state = status.get("status", "stop")
        log("Status {}".format(state))

        # Show clock if not playing
        if state != "play":
            if last_state != "clock":
                draw_clock()
                last_state = "clock"
            await asyncio.sleep_ms(POLL_INTERVAL_SLOW_MS)
            continue

        # Extract track information
        title  = hex_to_text(status.get("Title"))
        artist = hex_to_text(status.get("Artist"))
        album  = hex_to_text(status.get("Album"))

        track_id = "{}|{}|{}".format(title, artist, album)

        # Update display if track changed OR returning from clock OR no album art yet
        needs_update = (
            track_id != last_track_id or
            last_state == "clock" or
            (last_art_url is None and track_id == last_track_id)
        )

        if needs_update:
            if track_id != last_track_id:
                log("Track changed: {}".format(track_id))
                last_art_url = None  # Reset album art for new track
            elif last_state == "clock":
                log("Returning from clock, redrawing track")
            elif last_art_url is None:
                log("Retrying metadata fetch (previous attempt failed)")

            # Fetch metadata for album art URL
            meta = fetch_meta_info()
            art_url = None

            if meta:
                art_url = meta.get("albumArtURI")
                log("Album art URL: {}".format(art_url))
            else:
                log("Metadata fetch failed, will retry next poll")

            draw_track(title, artist, album, art_url)
            last_track_id = track_id
            last_state = "track"
            last_art_url = art_url  # Remember if we got album art
        else:
            log("Same track, skipping update")

        # Smart polling: Check time remaining
        poll_interval = POLL_INTERVAL_SLOW_MS

        try:
            # Try to get track position and duration (in milliseconds)
            totlen = int(status.get("totlen", 0))
            curpos = int(status.get("curpos", 0))

            if totlen > 0 and curpos >= 0:
                remaining_ms = totlen - curpos
                remaining_s = remaining_ms // 1000

                # Use fast polling if near end of track
                if remaining_s <= TRACK_END_THRESHOLD_S:
                    poll_interval = POLL_INTERVAL_FAST_MS
                    log("Near track end ({}s remaining), fast polling".format(remaining_s))
                else:
                    log("Track playing ({}s remaining), slow polling".format(remaining_s))
        except (ValueError, TypeError):
            # If we can't parse timing, use slow polling
            log("No timing info, using slow polling")

        await asyncio.sleep_ms(poll_interval)

# =======================
# BOOT
# =======================

def main():
    """Initialize WiFi, display clock, and start monitoring loop."""
    log("Boot")
    connect_wifi()
    draw_clock()
    log("Starting asyncio")
    asyncio.run(monitor())

main()
