# ==========================================================
# WiiM Now Playing / Clock for Pimoroni Presto (MicroPython)
# ==========================================================

# CRITICAL: Initialize PSRAM first (required for Presto)
import os
import psram
psram.mkramfs()

# Handle launch file (for app launcher compatibility)
try:
    with open("/ramfs/launch.txt", "r") as f:
        result = f.readline()
except OSError:
    result = ""

if result.endswith(".py"):
    os.remove("/ramfs/launch.txt")
    __import__(result[:-3])

# Core imports
import gc
import time
import machine
import uasyncio as asyncio

# =======================
# CREATE SINGLE PRESTO INSTANCE (like sample main.py)
# =======================
print("Initializing display...")
from presto import Presto

# Create THE ONE AND ONLY Presto instance
presto = Presto(ambient_light=False, full_res=True)
display = presto.display

# Clear display immediately (prevents garbage on screen)
BLACK = display.create_pen(0, 0, 0)
display.set_pen(BLACK)
display.clear()
presto.update()
print("Display cleared")

# Get dimensions
WIDTH, HEIGHT = display.get_bounds()
print("Display size: {}x{}".format(WIDTH, HEIGHT))

# =======================
# INITIALIZE DISPLAY MANAGER WITH OUR PRESTO
# =======================
print("Initializing display manager...")
import display_manager
display_manager.init_display(presto)  # Pass our presto instance
print("Display manager initialized")

# Now import everything else
from config import POLL_INTERVAL_SLOW_MS, POLL_INTERVAL_FAST_MS, TRACK_END_THRESHOLD_S
from utils import log, hex_to_text
from wifi import connect_wifi, sync_ntp
# Import music client adapter (supports both WiiM and Roon)
from music_client import (
    fetch_player_status, fetch_meta_info,
    pause_playback, resume_playback, next_track, previous_track, load_preset,
    fetch_presets
)
from display_manager import draw_clock, draw_track, draw_playback_buttons, show_loading_message, set_preset_labels
from touch_manager import TouchManager
from weather import get_weather

print("All imports complete")

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
    last_buttons_visible = False
    last_minute = -1  # Track last displayed minute for clock redraws
    last_weather_desc = "" # Track weather for redraws

    # Timing tracking
    last_status_fetch = 0
    last_weather_fetch = 0
    last_wifi_check = 0
    wifi_fail_count = 0
    last_ntp_sync = time.ticks_ms()   # Already synced at boot; resync after 1 hour
    last_preset_fetch = 0              # Fetch presets soon after boot, then every 30 min
    NTP_SYNC_INTERVAL_MS = 3600 * 1000
    PRESET_REFRESH_INTERVAL_MS = 1800 * 1000
    
    import network
    wlan = network.WLAN(network.STA_IF)

    while True:
        gc.collect()
        now = time.ticks_ms()

        # ============================================
        # WIFI HEALTH CHECK
        # ============================================
        if time.ticks_diff(now, last_wifi_check) >= 5000:
            last_wifi_check = now
            if not wlan.isconnected():
                wifi_fail_count += 1
                log("WiFi connection lost! Attempting to reconnect (failure {})...".format(wifi_fail_count))
                show_loading_message("WiFi Lost - Reconnecting...")
                
                try:
                    connect_wifi()
                    log("WiFi reconnected successfully")
                    wifi_fail_count = 0
                    # Force a full refresh of everything
                    screen_state = None
                    last_status_fetch = 0
                except Exception as e:
                    log("WiFi reconnection failed: {}".format(e))
                    
                    # If we fail for a long time (e.g. 12 * 5s = 60s), 
                    # we could consider more drastic action, but for now 
                    # let's just keep trying. The improved connect_wifi handles 
                    # its own retries and resets.
                    
                    if wifi_fail_count >= 24: # ~2 minutes of failure
                        log("CRITICAL: WiFi persistent failure. Restarting system...")
                        show_loading_message("WiFi Failed - Restarting...")
                        time.sleep(2)
                        import machine
                        machine.reset()
                        
                    continue
            else:
                wifi_fail_count = 0

        # ============================================
        # HOURLY NTP RESYNC
        # ============================================
        if time.ticks_diff(now, last_ntp_sync) >= NTP_SYNC_INTERVAL_MS:
            last_ntp_sync = now
            sync_ntp()

        # ============================================
        # PERIODIC PRESET REFRESH (every 30 min)
        # ============================================
        if time.ticks_diff(now, last_preset_fetch) >= PRESET_REFRESH_INTERVAL_MS:
            last_preset_fetch = now
            labels = fetch_presets()
            if labels:
                set_preset_labels(labels)

        # ============================================
        # PRIORITY: HANDLE TOUCHES FIRST!
        # ============================================
        # Check for touches BEFORE doing any slow API calls
        # This ensures immediate button display/reponse

        if screen_state == STATE_CLOCK:
            touch_action = touch_mgr.handle_touch_on_clock_screen()
            if touch_action == "show_resume":
                # First touch - show appropriate buttons based on player state
                if player_state == "pause":
                    # Paused: show resume button
                    log(">>> SHOWING RESUME BUTTON (immediate)")
                    draw_clock(show_resume=True, show_presets=False)
                else:
                    # Stopped: show preset buttons to start playback
                    log(">>> SHOWING PRESET BUTTONS (immediate, stopped state)")
                    draw_clock(show_resume=False, show_presets=True)
                presto.update()
                last_status_fetch = now # Delay next status fetch
                continue

            elif touch_action == "show_presets":
                # Touch outside resume button - show preset buttons too
                log(">>> SHOWING PRESET BUTTONS (immediate)")
                draw_clock(show_resume=player_state == "pause", show_presets=True)
                presto.update()
                last_status_fetch = now # Delay next status fetch
                continue

            elif touch_action == "hide_buttons":
                log(">>> HIDING CLOCK BUTTONS (immediate)")
                draw_clock(show_resume=False, show_presets=False)
                presto.update()
                last_status_fetch = now # Delay next status fetch
                continue

            elif touch_action == "resume" and player_state == "pause":
                log(">>> RESUME PRESSED (immediate)")
                show_loading_message("Resuming...")
                if resume_playback():
                    touch_mgr.hide_resume_button()
                    screen_state = None
                    player_state = None
                    # WiiM needs a moment to resume — wait before polling
                    show_loading_message("Starting...")
                    await asyncio.sleep_ms(2000)
                    last_status_fetch = 0
                continue

            elif touch_action and touch_action.startswith("preset_"):
                preset_num = int(touch_action.split("_")[1])
                log(">>> PRESET {} PRESSED (immediate)".format(preset_num))
                show_loading_message("Loading preset...")
                if load_preset(preset_num):
                    touch_mgr.hide_resume_button()
                    screen_state = None
                    player_state = None
                    # WiiM needs time to buffer and start the stream
                    show_loading_message("Starting stream...")
                    await asyncio.sleep_ms(3000)
                    last_status_fetch = 0
                continue

        elif screen_state == STATE_PLAYING:
            touch_action = touch_mgr.handle_touch_on_playing_screen()
            if touch_action == "show_buttons":
                # Immediately show buttons without waiting for status
                log(">>> SHOWING PLAYBACK BUTTONS (immediate)")
                draw_playback_buttons()
                presto.update()
                last_status_fetch = now # Delay next status fetch
                continue

            elif touch_action == "hide_buttons":
                log(">>> HIDING PLAYBACK BUTTONS (immediate)")
                # Force immediate redraw without buttons
                # But we need status info for that. Let's just set buttons_visible to false
                # and let the normal loop handle it by resetting last_status_fetch
                last_status_fetch = 0
                await asyncio.sleep_ms(50)
                continue

            elif touch_action == "pause":
                log(">>> PAUSE PRESSED (immediate)")
                if pause_playback():
                    touch_mgr.hide_playback_buttons()
                    # Show resume button and update TouchManager state
                    touch_mgr.show_resume_button()
                    # Immediately show clock screen
                    log("Drawing clock after pause")
                    draw_clock(show_resume=True, show_presets=False)
                    presto.update()
                    screen_state = STATE_CLOCK
                    last_status_fetch = now
                    await asyncio.sleep_ms(200)
                continue

            elif touch_action == "next":
                log(">>> NEXT PRESSED (immediate)")
                if next_track():
                    # Force redraw with new track
                    last_track_id = None
                    last_status_fetch = 0 # Fetch status immediately
                    await asyncio.sleep_ms(200)
                continue

            elif touch_action == "prev":
                log(">>> PREV PRESSED (immediate)")
                if previous_track():
                    # Force redraw with new track
                    last_track_id = None
                    last_status_fetch = 0 # Fetch status immediately
                    await asyncio.sleep_ms(200)
                continue

        # ============================================
        # PERIODIC PLAYER STATUS FETCH
        # ============================================
        
        # Determine poll interval
        buttons_visible = touch_mgr.is_resume_button_visible() if screen_state == STATE_CLOCK else touch_mgr.are_playback_buttons_visible()
        
        if screen_state == STATE_CLOCK:
            if buttons_visible:
                poll_interval_ms = 1000  # Check status for button timeout
            else:
                poll_interval_ms = 5000  # Check status occasionally even in clock mode
        else:
            # Playing screen
            if buttons_visible:
                poll_interval_ms = 2000  # Check every 2 seconds for button timeout
            else:
                poll_interval_ms = POLL_INTERVAL_SLOW_MS
                # Note: near end of track check is done AFTER we have status

        if time.ticks_diff(now, last_status_fetch) >= poll_interval_ms:
            last_status_fetch = now
            
            status = fetch_player_status()
            if not status:
                status_failures += 1
                log("Status fetch failed ({}/8) - keeping current display".format(status_failures))
    
                if status_failures >= 8:
                    # Connection really lost after 8 failures - show clock
                    if screen_state != STATE_CLOCK:
                        log("Connection lost after {} failures - switching to clock".format(status_failures))
                        draw_clock(show_resume=False)
                        screen_state = STATE_CLOCK
                    status_failures = 0
                else:
                    # Back off retry: 3s after first fail, up to 15s — avoids socket exhaustion
                    backoff_ms = min(3000 * status_failures, 15000)
                    last_status_fetch = now - poll_interval_ms + backoff_ms
                    gc.collect()  # Reclaim any leaked socket buffers
                
                await asyncio.sleep_ms(50)
                continue
    
            status_failures = 0
            player_state = status.get("status", "stop")
            # log("Player: {}".format(player_state)) # Too chatty for high-freq loop

            # ============================================
            # HANDLE CLOCK SCREEN (Stopped/Paused)
            # ============================================
    
            if player_state != "play":
                is_paused = (player_state == "pause")
                buttons_visible = touch_mgr.is_resume_button_visible()
                current_minute = time.localtime()[4]
                
                # Get weather to check for changes
                weather = get_weather()
                weather_desc = "{}{}".format(
                    weather.get("temperature", ""), 
                    weather.get("description", "")
                ) if weather else ""
    
                # Draw clock if not already showing, minute changed, or weather changed
                weather_changed = (weather_desc != last_weather_desc)
                if screen_state != STATE_CLOCK or current_minute != last_minute or weather_changed:
                    log("Drawing clock (paused={}, min_changed={}, weather_changed={})".format(
                        is_paused, current_minute != last_minute, weather_changed
                    ))
                    # Don't auto-show buttons, wait for touch
                    draw_clock(show_resume=False, show_presets=False)
                    screen_state = STATE_CLOCK
                    last_minute = current_minute
                    last_weather_desc = weather_desc
                    log("Screen state: CLOCK")
                
                # Check for near end of track if we WERE playing (though we are now stopped/paused)
                # Not really needed for clock screen
                
                await asyncio.sleep_ms(50)
                continue
    
            # ============================================
            # HANDLE PLAYING SCREEN
            # ============================================
    
            # Get track info
            title = hex_to_text(status.get("Title"))
            artist = hex_to_text(status.get("Artist"))
            album = hex_to_text(status.get("Album"))
            track_id = "{}|{}|{}".format(title, artist, album)
    
            # Get button visibility state
            buttons_visible = touch_mgr.are_playback_buttons_visible()
    
            # Determine if we need to redraw
            track_changed = (track_id != last_track_id)
            returning_from_clock = (screen_state != STATE_PLAYING)
            art_needs_retry = (last_art_url == False and art_fetch_failures < 3)
            buttons_changed = (buttons_visible != last_buttons_visible)
    
            needs_redraw = track_changed or returning_from_clock or art_needs_retry or buttons_changed
    
            if needs_redraw:
                log("Redrawing: track_changed={}, from_clock={}, art_retry={}, buttons_changed={}".format(
                    track_changed, returning_from_clock, art_needs_retry, buttons_changed
                ))
    
                # Fetch album art URL only if track actually changed
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
                last_buttons_visible = buttons_visible
                screen_state = STATE_PLAYING
                last_minute = -1  # Reset minute so clock redraws when we return to it
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

            # Adjust poll interval if near end of track
            try:
                totlen = int(status.get("totlen", 0))
                curpos = int(status.get("curpos", 0))
                if totlen > 0 and curpos >= 0:
                    remaining_s = (totlen - curpos) // 1000
                    if remaining_s <= TRACK_END_THRESHOLD_S:
                        # Near end of track, fetch status more frequently
                        last_status_fetch = now - poll_interval_ms + POLL_INTERVAL_FAST_MS
            except (ValueError, TypeError):
                pass

        # Small sleep to keep loop responsive to touches and other tasks
        await asyncio.sleep_ms(100)

# =======================
# BOOT HELPER FUNCTIONS
# =======================

def show_boot_message(message, color=(255, 255, 255)):
    """Show a boot status message on screen."""
    try:
        display.set_pen(BLACK)
        display.clear()
        pen = display.create_pen(*color)
        display.set_pen(pen)
        display.text(message, 10, HEIGHT // 2 - 10, WIDTH - 20, 3)
        presto.update()
    except Exception as e:
        print("Failed to show boot message: {}".format(e))

def show_wifi_error(wifi_error):
    """Show WiFi error with SSID info and halt."""
    print("=" * 50)
    print("WiFi Connection Failed!")
    print("=" * 50)

    try:
        from secrets import WIFI_SSID, WIIM_IP
        print("SSID: {}".format(WIFI_SSID))
        print("WiiM IP: {}".format(WIIM_IP))

        # Draw error screen
        red_pen = display.create_pen(255, 0, 0)
        white_pen = display.create_pen(255, 255, 255)

        display.set_pen(red_pen)
        display.clear()
        display.set_pen(white_pen)

        display.text("WiFi Failed!", 10, 10, 460, 3)
        display.text("SSID: {}".format(WIFI_SSID), 10, 50, 460, 2)
        display.text("WiiM IP: {}".format(WIIM_IP), 10, 80, 460, 2)
        display.text("Check secrets.py", 10, 120, 460, 2)
        display.text("Error: {}".format(str(wifi_error)[:30]), 10, 150, 460, 2)
        display.text("Power cycle to retry", 10, 400, 460, 2)

        print("Error screen created")
    except Exception as display_error:
        print("Failed to show error: {}".format(display_error))

    # Wait 60 seconds then return so the caller can retry
    print("Waiting 60s before retry...")
    for remaining in range(60, 0, -10):
        try:
            display.set_pen(display.create_pen(255, 0, 0))
            display.clear()
            display.set_pen(display.create_pen(255, 255, 255))
            display.text("WiFi Failed!", 10, 10, 460, 3)
            display.text("SSID: {}".format(WIFI_SSID), 10, 50, 460, 2)
            display.text("Retrying in {}s...".format(remaining), 10, 190, 460, 2)
            presto.update()
        except Exception:
            pass
        time.sleep(10)

def show_error(error_msg):
    """Show generic error on screen and halt."""
    print("FATAL ERROR: {}".format(error_msg))
    try:
        red_pen = display.create_pen(255, 0, 0)
        white_pen = display.create_pen(255, 255, 255)

        display.set_pen(red_pen)
        display.clear()
        display.set_pen(white_pen)
        display.text("ERROR:", 10, 10, WIDTH - 20, 3)
        display.text(str(error_msg)[:100], 10, 40, WIDTH - 20, 2)
        display.text("Power cycle to retry", 10, HEIGHT - 30, WIDTH - 20, 2)
    except:
        pass

    # Keep display updated
    while True:
        presto.update()
        time.sleep(1)

# =======================
# BOOT SEQUENCE
# =======================

def main():
    """Boot sequence with visual feedback."""
    try:
        # Show we're starting
        show_boot_message("Starting...")
        time.sleep(0.5)

        log("Boot sequence starting")

        # Connect to WiFi - keep retrying every 60s if router is down
        while True:
            show_boot_message("Connecting to WiFi...")
            time.sleep(0.5)
            try:
                connect_wifi()
                log("WiFi connected")
                break
            except Exception as wifi_error:
                show_wifi_error(wifi_error)
                log("Retrying WiFi connection...")

        # Fetch preset names from WiiM; fall back to config defaults so buttons
        # are always initialised with correct touch areas before the first draw.
        show_boot_message("Loading presets...")
        from config import PRESET_LABELS as _default_labels
        labels = fetch_presets()
        if labels:
            log("Presets loaded from WiiM: {}".format(labels))
        else:
            log("Preset fetch failed, using config defaults")
            labels = _default_labels
        set_preset_labels(labels)

        # Show initial clock
        show_boot_message("Loading...")
        time.sleep(0.3)
        draw_clock()
        log("Initial screen drawn")

        # Start main loop
        log("Starting monitor loop")
        asyncio.run(monitor())

    except KeyboardInterrupt:
        log("Keyboard interrupt")
        show_boot_message("Stopped", (255, 200, 0))
        time.sleep(2)

    except MemoryError as e:
        show_error("Out of memory: {}".format(e))

    except ImportError as e:
        show_error("Import failed: {}".format(e))

    except Exception as e:
        import sys
        sys.print_exception(e)
        show_error("Error: {}".format(e))

# Run main
main()
