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
from color_utils import get_album_art_colors, sample_jpeg_colors, get_contrast_color, adjust_color_for_visibility

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
YELLOW = display.create_pen(255, 200, 0)
LIGHT_GRAY = display.create_pen(180, 180, 180)
GRAY = display.create_pen(140, 140, 140)

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

        # Time at top (largest) - white
        display.set_pen(WHITE)
        vector.set_font_size(200)
        vector.text(time_str, margin, 200)  # Position baseline, not top

        # Temperature (very large) - yellow to stand out
        display.set_pen(YELLOW)
        vector.set_font_size(100)
        temp_text = weather["temperature"]
        vector.text(temp_text, margin, 310)

        # Weather description (large, readable) - light gray
        display.set_pen(LIGHT_GRAY)
        vector.set_font_size(48)
        desc_text = weather["description"]
        vector.text(desc_text, margin, 390)

        # Location (medium, at bottom) - medium gray
        display.set_pen(GRAY)
        vector.set_font_size(32)
        loc_text = weather["location"]
        vector.text(loc_text, margin, 450)

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
        tuple: (success: bool, colors: dict or None)
            success: True if decode worked
            colors: {'avg_color': (r,g,b)} if sampling worked, None otherwise
    """
    try:
        log("Fetch art {}".format(art_url))

        jpeg = fetch_url(art_url)
        if not jpeg:
            return False, None

        # Clear and decode JPEG with scaling to fit display
        display.set_pen(BLACK)
        display.clear()

        jpd.open_RAM(memoryview(jpeg))

        # Get image dimensions
        img_width, img_height = jpd.get_width(), jpd.get_height()
        log("Image size: {}x{}".format(img_width, img_height))

        # Note: JPEG color sampling doesn't work reliably because JPEG files
        # are compressed (DCT coefficients, not RGB pixels). Disabled for now.
        # sampled_colors = sample_jpeg_colors(jpeg, img_width, img_height)
        sampled_colors = None

        # Choose smallest scale that fills the display (minimize cropping/borders)
        # Check scales from smallest image to largest
        scale = jpegdec.JPEG_SCALE_FULL
        scale_factor = 1

        for s, f in [
            (jpegdec.JPEG_SCALE_QUARTER, 4),
            (jpegdec.JPEG_SCALE_HALF, 2),
            (jpegdec.JPEG_SCALE_FULL, 1),
        ]:
            w = img_width // f
            h = img_height // f
            if w >= WIDTH and h >= HEIGHT:
                # This scale fills/exceeds display, use it
                scale = s
                scale_factor = f
                break

        scaled_width = img_width // scale_factor
        scaled_height = img_height // scale_factor

        # Center the image on screen
        x = (WIDTH - scaled_width) // 2
        y = (HEIGHT - scaled_height) // 2

        log("Decoding {}x{} at ({}, {}) scale 1/{}".format(
            scaled_width, scaled_height, x, y, scale_factor))

        try:
            jpd.decode(x, y, scale)
            log("Album art decoded successfully")
        except MemoryError:
            log("Album art decode failed (OOM)")
            return False, None

        # Don't update display yet - let draw_track() do it after adding text
        log("Album art decoded")
        return True, sampled_colors

    except Exception as e:
        log("Album art error: {}".format(e))
        return False, None

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
    art_colors = None

    # Draw album art first if available (just decodes, doesn't update)
    if art_url:
        art_success, art_colors = draw_album_art(art_url)
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

    # Use colors from JPEG sampling if available
    bg_pen = None
    text_pen = WHITE

    if art_success and art_colors and 'avg_color' in art_colors:
        try:
            bg_r, bg_g, bg_b = art_colors['avg_color']

            # Adjust color for better visibility
            bg_r, bg_g, bg_b = adjust_color_for_visibility(bg_r, bg_g, bg_b)

            # Get contrasting text color
            txt_r, txt_g, txt_b = get_contrast_color(bg_r, bg_g, bg_b)

            bg_pen = display.create_pen(bg_r, bg_g, bg_b)
            text_pen = display.create_pen(txt_r, txt_g, txt_b)

            log("Using JPEG colors - bg:({},{},{}), text:({},{},{})".format(
                bg_r, bg_g, bg_b, txt_r, txt_g, txt_b))
        except Exception as e:
            log("Color processing failed: {}".format(e))

    # Fallback: Use semi-transparent dark gray (works with any album art)
    if bg_pen is None:
        log("Using semi-transparent overlay fallback")
        # Dark gray with slight transparency effect (visually blends better)
        bg_pen = display.create_pen(20, 20, 20)  # Very dark gray
        text_pen = WHITE

    # Helper function to draw text with colored background
    def draw_text_with_bg(text, x, y, font_size):
        vector.set_font_size(font_size)

        # Try to measure text width accurately
        text_width = None
        try:
            measured = vector.measure_text(text)
            if measured:
                # Extract width (measure_text might return tuple or int)
                try:
                    text_width = measured[0]  # Try to extract from tuple (width, height)
                except (TypeError, IndexError):
                    text_width = measured  # It's already an int

                if text_width and text_width > 10:
                    log("Measured '{}...' width: {}px at size {}".format(
                        text[:15], text_width, font_size))
                else:
                    # Invalid measurement
                    text_width = None
        except Exception as e:
            log("measure_text error: {}".format(e))
            pass

        # Fallback: estimate based on font size (Roboto Medium averages ~0.46em per char)
        if text_width is None:
            text_width = int(len(text) * font_size * 0.46)
            log("Estimated '{}...' width: {}px at size {}".format(
                text[:15], text_width, font_size))

        # Don't exceed screen
        text_width = min(text_width, WIDTH - x - 10)

        # Draw colored background box
        display.set_pen(bg_pen)
        display.rectangle(x - padding, y - padding, text_width + padding * 2, font_size + padding * 2)

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
