# ==========================================================
# WiiM Now Playing / Clock for Pimoroni Presto (MicroPython)
# ==========================================================

import gc
import uasyncio as asyncio
from config import POLL_INTERVAL_MS
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
    """
    log("Enter monitor loop")

    last_state = None
    last_track_id = None

    while True:
        gc.collect()

        # Fetch player status
        status = fetch_player_status()
        if not status:
            if last_state != "clock":
                draw_clock()
                last_state = "clock"
            await asyncio.sleep_ms(POLL_INTERVAL_MS)
            continue

        state = status.get("status", "stop")
        log("Status {}".format(state))

        # Show clock if not playing
        if state != "play":
            if last_state != "clock":
                draw_clock()
                last_state = "clock"
            await asyncio.sleep_ms(POLL_INTERVAL_MS)
            continue

        # Extract track information
        title  = hex_to_text(status.get("Title"))
        artist = hex_to_text(status.get("Artist"))
        album  = hex_to_text(status.get("Album"))

        track_id = "{}|{}|{}".format(title, artist, album)

        # Only update display if track has changed
        if track_id != last_track_id:
            # Fetch metadata for album art URL
            meta = fetch_meta_info()
            art_url = None

            if meta:
                art_url = meta.get("albumArtURI")

            draw_track(title, artist, album, art_url)
            last_track_id = track_id
            last_state = "track"

        await asyncio.sleep_ms(POLL_INTERVAL_MS)

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
