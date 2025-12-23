# ==========================================================
# Display Manager Module
# ==========================================================

import time
import gc
import jpegdec
from presto import Presto
from picovector import PicoVector, ANTIALIAS_FAST
from config import BACKLIGHT_BRIGHTNESS
from http_client import fetch_url
from utils import log
from weather import get_weather

# =======================
# DISPLAY INITIALIZATION
# =======================

log("Init Presto")
presto = Presto(ambient_light=False, full_res=True)
presto.set_backlight(BACKLIGHT_BRIGHTNESS)
display = presto.display

WIDTH, HEIGHT = display.get_bounds()

BLACK = display.create_pen(0, 0, 0)
WHITE = display.create_pen(255, 255, 255)

log("Init Vector")
vector = PicoVector(display)
vector.set_antialiasing(ANTIALIAS_FAST)
vector.set_font("Roboto-Medium.af", 14)
vector.set_font_letter_spacing(100)
vector.set_font_word_spacing(100)

jpd = jpegdec.JPEG(display)

# =======================
# DRAWING FUNCTIONS
# =======================

def clear_screen():
    """Clear the display to black."""
    display.set_pen(BLACK)
    display.clear()

def draw_clock():
    """Draw the current time with weather information."""
    clear_screen()

    # Draw time (large, centered)
    t = time.localtime()
    time_str = "{:02}:{:02}".format(t[3], t[4])

    display.set_pen(WHITE)

    # Fetch weather to adjust layout
    weather = get_weather()

    if weather:
        # With weather: time at top
        vector.set_font_size(120)
        tw = int(vector.measure_text(time_str)[0])
        x = (WIDTH - tw) // 2
        vector.text(time_str, x, 100)

        # Draw temperature (medium)
        vector.set_font_size(50)
        temp_text = weather["temperature"]
        tw = int(vector.measure_text(temp_text)[0])
        x = (WIDTH - tw) // 2
        vector.text(temp_text, x, 260)

        # Draw weather description (small)
        vector.set_font_size(24)
        desc_text = weather["description"]
        tw = int(vector.measure_text(desc_text)[0])
        x = (WIDTH - tw) // 2
        vector.text(desc_text, x, 320)

        # Draw location (tiny)
        vector.set_font_size(16)
        loc_text = weather["location"]
        tw = int(vector.measure_text(loc_text)[0])
        x = (WIDTH - tw) // 2
        vector.text(loc_text, x, 350)

        log("Clock with weather: {} {}".format(weather["temperature"], weather["description"]))
    else:
        # Without weather: time centered
        vector.set_font_size(180)
        tw = int(vector.measure_text(time_str)[0])
        x = (WIDTH - tw) // 2
        y = HEIGHT // 2
        vector.text(time_str, x, y)
        log("Clock (no weather data)")

    presto.update()

def draw_album_art(art_url):
    """
    Download and display album art from URL.
    Scales to fill the entire screen.

    Args:
        art_url: URL of album art image (JPEG)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        log("Fetch art {}".format(art_url))

        jpeg = fetch_url(art_url)
        if not jpeg:
            return False

        # Clear and decode JPEG with scaling to fit display
        display.set_pen(BLACK)
        display.clear()

        jpd.open_RAM(memoryview(jpeg))

        # Get image dimensions
        img_width, img_height = jpd.get_width(), jpd.get_height()
        log("Image size: {}x{}".format(img_width, img_height))

        # Try scaling options to fill screen, prefer better quality
        for scale in (
            jpegdec.JPEG_SCALE_HALF,
            jpegdec.JPEG_SCALE_QUARTER,
            jpegdec.JPEG_SCALE_EIGHTH,
        ):
            try:
                # Calculate scaled dimensions
                scale_factor = {
                    jpegdec.JPEG_SCALE_HALF: 2,
                    jpegdec.JPEG_SCALE_QUARTER: 4,
                    jpegdec.JPEG_SCALE_EIGHTH: 8,
                }.get(scale, 4)

                scaled_width = img_width // scale_factor
                scaled_height = img_height // scale_factor

                # Center the image on screen
                x = (WIDTH - scaled_width) // 2
                y = (HEIGHT - scaled_height) // 2

                # Ensure non-negative position
                x = max(0, x)
                y = max(0, y)

                log("Decoding at position ({}, {}) with scale {}".format(x, y, scale_factor))
                jpd.decode(x, y, scale)
                break
            except MemoryError:
                gc.collect()
        else:
            log("Album art decode failed (OOM)")
            return False

        # Don't update display yet - let draw_track() do it after adding text
        log("Album art decoded")
        return True

    except Exception as e:
        log("Album art error: {}".format(e))
        return False

def draw_track(title, artist, album, art_url=None):
    """
    Draw track information with optional album art.

    Args:
        title: Track title
        artist: Artist name
        album: Album name
        art_url: Optional URL for album art
    """
    # Ensure we have valid strings
    title = title or "Unknown"
    artist = artist or "Unknown Artist"

    # Draw album art first if available (just decodes, doesn't update)
    if art_url:
        if not draw_album_art(art_url):
            # If album art fails, just use black background
            clear_screen()
    else:
        # No album art, use black background
        clear_screen()

    # Draw dark background bar at bottom for text
    bar_height = 80
    bar_y = HEIGHT - bar_height

    # Create dark background
    dark_bg = display.create_pen(0, 0, 0)  # Black background
    display.set_pen(dark_bg)
    display.rectangle(0, bar_y, WIDTH, bar_height)

    # Draw text on top of dark background
    display.set_pen(WHITE)

    # Start text 8 pixels from top of bar
    text_y = bar_y + 8

    # Line 1: Track title (large, centered)
    vector.set_font_size(28)
    tw = int(vector.measure_text(title)[0])
    x = (WIDTH - tw) // 2
    vector.text(title, x, text_y)

    # Line 2: Artist (left) and Album (right)
    line2_y = text_y + 40

    # Artist on the left (larger)
    vector.set_font_size(18)
    artist_text = artist if artist else "Unknown Artist"
    vector.text(artist_text, 10, line2_y)

    # Album on the right (smaller, to distinguish from artist)
    if album:
        vector.set_font_size(15)
        album_tw = int(vector.measure_text(album)[0])
        album_x = WIDTH - album_tw - 10
        vector.text(album, album_x, line2_y + 2)  # Slight offset for visual distinction

    log("Text overlay: {} - {} - {}".format(title, artist, album))

    # Update display once with everything drawn
    presto.update()
    log("Draw track: {} - {}".format(title, artist))
