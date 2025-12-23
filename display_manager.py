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
from color_utils import get_album_art_colors

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

    log("Display size: {}x{}".format(WIDTH, HEIGHT))

    if weather:
        # Presto 480x480 display - left-aligned, properly spaced
        margin = 20

        # Time at top (largest) - y position accounts for font height
        vector.set_font_size(140)
        vector.text(time_str, margin, 160)  # Position baseline, not top

        # Temperature (very large)
        vector.set_font_size(100)
        temp_text = weather["temperature"]
        vector.text(temp_text, margin, 270)

        # Weather description (large, readable)
        vector.set_font_size(48)
        desc_text = weather["description"]
        vector.text(desc_text, margin, 350)

        # Location (medium, at bottom)
        vector.set_font_size(32)
        loc_text = weather["location"]
        vector.text(loc_text, margin, 420)

        log("Clock with weather: {} {} in {}".format(
            weather["temperature"], weather["description"], weather["location"]))
    else:
        # Without weather: time left-aligned
        vector.set_font_size(180)
        vector.text(time_str, 20, 240)  # Centered vertically
        log("Clock (no weather data)")

    log("Clock drawn")

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

        # Determine best scale to fit display (480x480)
        # If image is larger than display, scale it down to fit
        for scale in (
            jpegdec.JPEG_SCALE_FULL,
            jpegdec.JPEG_SCALE_HALF,
            jpegdec.JPEG_SCALE_QUARTER,
        ):
            scale_factor = {
                jpegdec.JPEG_SCALE_FULL: 1,
                jpegdec.JPEG_SCALE_HALF: 2,
                jpegdec.JPEG_SCALE_QUARTER: 4,
            }.get(scale, 1)

            scaled_width = img_width // scale_factor
            scaled_height = img_height // scale_factor

            # Calculate position to center or fit on screen
            if scaled_width > WIDTH or scaled_height > HEIGHT:
                # Image is larger than display, center it (will be cropped)
                x = (WIDTH - scaled_width) // 2
                y = (HEIGHT - scaled_height) // 2
            else:
                # Image fits, center it
                x = (WIDTH - scaled_width) // 2
                y = (HEIGHT - scaled_height) // 2

            # Clamp to screen bounds if negative
            x = max(0, x)
            y = max(0, y)

            log("Decoding {}x{} at ({}, {}) scale 1/{}".format(
                scaled_width, scaled_height, x, y, scale_factor))

            try:
                jpd.decode(x, y, scale)
                log("Album art decoded successfully")
                break
            except MemoryError:
                log("OOM at scale 1/{}, trying smaller".format(scale_factor))
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

    Returns:
        bool: True if album art was successfully displayed
    """
    # Ensure we have valid strings
    title = title or "Unknown"
    artist = artist or "Unknown Artist"

    art_success = False

    # Draw album art first if available (just decodes, doesn't update)
    if art_url:
        art_success = draw_album_art(art_url)
        if not art_success:
            # If album art fails, just use black background
            log("Album art failed, using black background")
            clear_screen()
    else:
        # No album art, use black background
        clear_screen()

    # Starting position from bottom
    text_x = 10  # Left margin
    padding = 6
    current_y = HEIGHT - 130
    text_region_height = 130

    # Get colors from album art if available, otherwise use defaults
    if art_success:
        try:
            colors = get_album_art_colors(display, current_y, text_region_height)
            bg_r, bg_g, bg_b = colors['background']
            txt_r, txt_g, txt_b = colors['text']
            bg_pen = display.create_pen(bg_r, bg_g, bg_b)
            text_pen = display.create_pen(txt_r, txt_g, txt_b)
            log("Using album colors - bg:({},{},{}), text:({},{},{})".format(
                bg_r, bg_g, bg_b, txt_r, txt_g, txt_b))
        except Exception as e:
            log("Color sampling failed: {}, using defaults".format(e))
            bg_pen = display.create_pen(0, 0, 0)
            text_pen = WHITE
    else:
        # No album art, use black background with white text
        bg_pen = display.create_pen(0, 0, 0)
        text_pen = WHITE

    # Helper function to draw text with colored background
    def draw_text_with_bg(text, x, y, font_size):
        vector.set_font_size(font_size)
        # Estimate text width (rough approximation since measure_text is unreliable)
        # Average character is ~0.6 of font size width
        est_width = int(len(text) * font_size * 0.6)
        est_width = min(est_width, WIDTH - x - 10)  # Don't exceed screen

        # Draw colored background box
        display.set_pen(bg_pen)
        display.rectangle(x - padding, y - padding, est_width + padding * 2, font_size + padding * 2)

        # Draw contrasting text on top
        display.set_pen(text_pen)
        vector.text(text, x, y + font_size)

    # Line 1: Track title (large)
    draw_text_with_bg(title, text_x, current_y, 38)
    log("Title: '{}'".format(title))

    # Line 2: Artist
    current_y += 50
    artist_text = artist if artist else "Unknown Artist"
    draw_text_with_bg(artist_text, text_x, current_y, 28)

    # Line 3: Album
    if album:
        current_y += 40
        draw_text_with_bg(album, text_x, current_y, 22)

    log("Text overlay: {} by {}".format(title, artist))

    # Update display once with everything drawn
    presto.update()
    log("Draw track: {} - {}".format(title, artist))

    return art_success
