# ==========================================================
# WiiM Now Playing / Clock for Pimoroni Presto (MicroPython)
# ==========================================================

import gc
import uasyncio as asyncio
from config import POLL_INTERVAL_SLOW_MS, POLL_INTERVAL_FAST_MS, TRACK_END_THRESHOLD_S
from utils import log, hex_to_text
from wifi import connect_wifi
from wiim_client import (
    fetch_player_status, fetch_meta_info,
    pause_playback, resume_playback, next_track, previous_track
)
from display_manager import draw_clock, draw_track, presto
from input_handler import check_playback_buttons, check_resume_button
from touch_handler import TouchHandler

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

    # Initialize touch handler (but don't enable yet)
    touch_handler = TouchHandler(presto)
    log("TouchHandler created")

    last_state = None
    last_track_id = None
    last_art_url = None  # Track if we successfully got album art
    status_failures = 0  # Count consecutive failures

    # Player pause state tracking
    player_paused = False

    while True:
        gc.collect()

        # Fetch player status with retry logic
        status = fetch_player_status()
        if not status:
            status_failures += 1
            log("Status fetch failed ({}/3)".format(status_failures))

            # Disable touch when connection fails
            if status_failures >= 1:
                touch_handler.disable()

            # Only show clock after 3 consecutive failures
            if status_failures >= 3:
                if last_state != "clock":
                    log("Multiple status failures, showing clock")
                    draw_clock()
                    last_state = "clock"
                status_failures = 0  # Reset counter

            await asyncio.sleep_ms(POLL_INTERVAL_SLOW_MS)
            continue

        # Reset failure counter and enable touch on success
        status_failures = 0
        if not touch_handler.enabled:
            touch_handler.enable()
            log("TouchHandler enabled (connection successful)")

        state = status.get("status", "stop")
        log("Status {}".format(state))

        # Track pause state separately from stop
        player_paused = (state == "pause")

        # Show clock if not playing
        if state != "play":
            # Check resume button if paused
            if player_paused:
                log("Player is paused, checking resume button...")

            if player_paused and check_resume_button():
                log("Resume button pressed")
                if resume_playback():
                    # Wait for state to update
                    await asyncio.sleep_ms(500)
                    # Force track redraw on next iteration
                    last_state = None
                    continue

            # Draw clock with resume button if paused
            if last_state != "clock":
                draw_clock(show_resume=player_paused)
                last_state = "clock"

            await asyncio.sleep_ms(POLL_INTERVAL_SLOW_MS)
            continue

        # ============================================
        # NOW PLAYING SCREEN
        # ============================================

        # Extract track information
        title  = hex_to_text(status.get("Title"))
        artist = hex_to_text(status.get("Artist"))
        album  = hex_to_text(status.get("Album"))

        track_id = "{}|{}|{}".format(title, artist, album)

        # Check if screen was touched (shows buttons)
        if touch_handler.was_screen_touched():
            log(">>> Touch detected from handler")
            touch_handler.show_buttons()

        # Get button visibility from handler
        buttons_visible = touch_handler.are_buttons_visible()

        # Button press handling
        if buttons_visible:
            log("Buttons are visible, checking for button presses...")
            button_action = check_playback_buttons()
            log("Button action result: {}".format(button_action))

            if button_action == "prev":
                log(">>> PREVIOUS BUTTON ACTION")
                if previous_track():
                    await asyncio.sleep_ms(500)
                    last_track_id = None  # Force redraw
                    touch_handler.hide_buttons()

            elif button_action == "pause":
                log(">>> PAUSE BUTTON ACTION")
                if pause_playback():
                    # Will transition to clock on next iteration
                    player_paused = True
                    touch_handler.hide_buttons()
                    await asyncio.sleep_ms(500)
                    continue

            elif button_action == "next":
                log(">>> NEXT BUTTON ACTION")
                if next_track():
                    await asyncio.sleep_ms(500)
                    last_track_id = None  # Force redraw
                    touch_handler.hide_buttons()

        # Update display if track changed OR returning from clock OR album art failed
        needs_update = (
            track_id != last_track_id or
            last_state == "clock" or
            last_art_url == False  # False means previous art fetch failed
        )

        if needs_update:
            if track_id != last_track_id:
                log("Track changed: {}".format(track_id))
                last_art_url = None  # Reset album art for new track
            elif last_state == "clock":
                log("Returning from clock, redrawing track")
            elif last_art_url == False:
                log("Retrying album art fetch (previous attempt failed)")

            # Fetch metadata for album art URL
            meta = fetch_meta_info()
            art_url = None

            if meta:
                art_url = meta.get("albumArtURI")
                log("Album art URL: {}".format(art_url))
            else:
                log("Metadata fetch failed, will retry next poll")

            # Draw track with button visibility parameter
            art_displayed = draw_track(title, artist, album, art_url, show_buttons=buttons_visible)

            last_track_id = track_id
            last_state = "track"

            # Track album art success: True if displayed, False if failed, None if no URL
            if art_url:
                last_art_url = art_displayed  # True or False
            else:
                last_art_url = None  # No art URL provided
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
