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
    pause_playback, resume_playback, next_track, previous_track, load_preset
)
from display_manager import draw_clock, draw_track, draw_playback_buttons, presto
from touch_manager import TouchManager

# =======================
# SCREEN STATES
# =======================

STATE_CLOCK = "clock"  # Showing clock/weather (stopped or paused)
STATE_PLAYING = "playing"  # Showing now playing (music playing)

# =======================
# MAIN MONITOR LOOP
# =======================

async def monitor():
    """Main monitoring loop."""
    log("Enter monitor loop")

    # Initialize touch manager
    touch_mgr = TouchManager(presto)
    touch_mgr.enable()

    # State tracking
    screen_state = None  # What's currently shown on screen
    player_state = None  # Player status (play/pause/stop)

    last_track_id = None
    last_art_url = None
    cached_art_url = None
    art_fetch_failures = 0
    status_failures = 0

    while True:
        gc.collect()

        # ============================================
        # FETCH PLAYER STATUS
        # ============================================

        status = fetch_player_status()
        if not status:
            status_failures += 1
            log("Status fetch failed ({}/3)".format(status_failures))

            if status_failures >= 3:
                # Show clock on repeated failures
                if screen_state != STATE_CLOCK:
                    log("Connection lost - showing clock")
                    draw_clock(show_resume=False)
                    screen_state = STATE_CLOCK
                status_failures = 0

            await asyncio.sleep_ms(POLL_INTERVAL_SLOW_MS)
            continue

        status_failures = 0
        player_state = status.get("status", "stop")
        log("Player: {}".format(player_state))

        # ============================================
        # HANDLE CLOCK SCREEN (Stopped/Paused)
        # ============================================

        if player_state != "play":
            is_paused = (player_state == "pause")

            # Handle touch on clock screen
            touch_action = touch_mgr.handle_touch_on_clock_screen()
            buttons_visible = touch_mgr.is_resume_button_visible()

            # Handle touch actions
            if touch_action == "resume" and is_paused:
                log(">>> RESUME PRESSED")
                if resume_playback():
                    touch_mgr.hide_resume_button()
                    await asyncio.sleep_ms(500)
                    # Force transition to playing screen
                    screen_state = None
                    player_state = None
                    continue

            elif touch_action and touch_action.startswith("preset_"):
                # Handle preset button press
                preset_num = int(touch_action.split("_")[1])
                log(">>> PRESET {} PRESSED".format(preset_num))
                if load_preset(preset_num):
                    touch_mgr.hide_resume_button()
                    await asyncio.sleep_ms(500)
                    # Force transition to playing screen
                    screen_state = None
                    player_state = None
                    continue

            elif touch_action == "show_buttons" or touch_action == "hide_buttons":
                # Redraw clock with updated button visibility
                log(">>> REDRAW CLOCK - Buttons visible: {}".format(buttons_visible))
                draw_clock(show_resume=buttons_visible and is_paused, show_presets=buttons_visible)
                presto.update()

            # Draw clock if not already showing (or needs redrawing)
            if screen_state != STATE_CLOCK:
                log("Drawing clock (paused={})".format(is_paused))
                # Don't auto-show buttons, wait for touch
                draw_clock(show_resume=False, show_presets=False)
                screen_state = STATE_CLOCK
                log("Screen state: CLOCK")

            # Use faster polling when buttons are visible
            poll_ms = 100 if buttons_visible else (1000 if is_paused else POLL_INTERVAL_SLOW_MS)
            await asyncio.sleep_ms(poll_ms)
            continue

        # ============================================
        # HANDLE PLAYING SCREEN
        # ============================================

        # Get track info
        title = hex_to_text(status.get("Title"))
        artist = hex_to_text(status.get("Artist"))
        album = hex_to_text(status.get("Album"))
        track_id = "{}|{}|{}".format(title, artist, album)

        # Handle touch on playing screen
        touch_action = touch_mgr.handle_touch_on_playing_screen()
        buttons_visible = touch_mgr.are_playback_buttons_visible()

        # Handle button actions
        if touch_action == "pause":
            log(">>> PAUSE PRESSED")
            if pause_playback():
                touch_mgr.hide_playback_buttons()
                await asyncio.sleep_ms(500)
                # Force transition to clock
                screen_state = None
                continue

        elif touch_action == "next":
            log(">>> NEXT PRESSED")
            if next_track():
                await asyncio.sleep_ms(500)
                last_track_id = None  # Force redraw

        elif touch_action == "prev":
            log(">>> PREV PRESSED")
            if previous_track():
                await asyncio.sleep_ms(500)
                last_track_id = None  # Force redraw

        elif touch_action == "show_buttons":
            # Just draw buttons on top of existing screen
            log(">>> SHOWING BUTTONS")
            draw_playback_buttons()
            presto.update()

        elif touch_action == "hide_buttons":
            # Force redraw to remove buttons
            log(">>> HIDING BUTTONS")
            last_track_id = None  # Force redraw

        # Determine if we need to redraw
        track_changed = (track_id != last_track_id)
        returning_from_clock = (screen_state != STATE_PLAYING)
        art_needs_retry = (last_art_url == False and art_fetch_failures < 3)

        needs_redraw = track_changed or returning_from_clock or art_needs_retry

        if needs_redraw:
            log("Redrawing: track_changed={}, from_clock={}, art_retry={}".format(
                track_changed, returning_from_clock, art_needs_retry
            ))

            # Fetch album art URL if needed
            if track_changed or returning_from_clock or cached_art_url is None:
                meta = fetch_meta_info()
                if meta:
                    cached_art_url = meta.get("albumArtURI")
                    log("Album art URL: {}".format(cached_art_url))
                else:
                    log("Metadata fetch failed")

            # Draw track
            art_displayed = draw_track(
                title, artist, album,
                cached_art_url,
                show_buttons=buttons_visible
            )

            # Update state
            last_track_id = track_id
            screen_state = STATE_PLAYING
            log("Screen state: PLAYING")

            # Track art success/failure
            if cached_art_url:
                last_art_url = art_displayed
                if art_displayed:
                    art_fetch_failures = 0
                    log("Album art OK")
                else:
                    art_fetch_failures += 1
                    log("Album art failed ({}/3)".format(art_fetch_failures))
            else:
                last_art_url = None
                art_fetch_failures = 0

        # Determine poll interval
        if buttons_visible:
            poll_interval = 100  # Very fast when buttons visible
        else:
            poll_interval = 1000  # 1 second default during playback

            # Check for track end (fast polling)
            try:
                totlen = int(status.get("totlen", 0))
                curpos = int(status.get("curpos", 0))

                if totlen > 0 and curpos >= 0:
                    remaining_s = (totlen - curpos) // 1000
                    if remaining_s <= TRACK_END_THRESHOLD_S:
                        poll_interval = POLL_INTERVAL_FAST_MS

            except (ValueError, TypeError):
                pass

        await asyncio.sleep_ms(poll_interval)

# =======================
# BOOT
# =======================

def main():
    """Boot sequence."""
    try:
        log("Boot")
        connect_wifi()
        draw_clock()
        log("Starting monitor loop")
        asyncio.run(monitor())
    except Exception as e:
        # Show error on screen if possible
        log("FATAL ERROR: {}".format(e))
        try:
            from display_manager import display, presto
            display.set_pen(display.create_pen(255, 0, 0))
            display.clear()
            display.set_pen(display.create_pen(255, 255, 255))
            display.text("ERROR: {}".format(str(e)[:50]), 10, 10, 460, 3)
            presto.update()
        except:
            pass
        # Keep running so we can see the error
        import time
        while True:
            time.sleep(1)

main()
