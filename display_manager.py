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
    """Draw the current time as a large clock display."""
    clear_screen()

    t = time.localtime()
    time_str = "{:02}:{:02}".format(t[3], t[4])

    display.set_pen(WHITE)
    vector.set_font_size(200)
    vector.text(time_str, 20, HEIGHT // 2)

    presto.update()
    log("Draw clock")

def draw_album_art(art_url):
    """
    Download and display album art from URL.

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

        # Try increasingly aggressive downscaling to handle memory constraints
        for scale in (
            jpegdec.JPEG_SCALE_FULL,
            jpegdec.JPEG_SCALE_HALF,
            jpegdec.JPEG_SCALE_QUARTER,
        ):
            try:
                jpd.decode(30, 0, scale)
                break
            except MemoryError:
                gc.collect()
        else:
            log("Album art decode failed (OOM)")
            return False

        # FIX: Update display to show the decoded image
        presto.update()
        log("Album art displayed")
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
    # Draw album art first if available
    if art_url:
        if not draw_album_art(art_url):
            # Fallback to clock if album art fails
            draw_clock()
    else:
        draw_clock()

    # Draw text overlay on top of album art or clock
    display.set_pen(WHITE)

    y = HEIGHT - 100

    vector.set_font_size(28)
    tw = int(vector.measure_text(title)[0])
    x = (WIDTH - tw) // 2
    vector.text(x, y, title)

    vector.set_font_size(22)
    tw = int(vector.measure_text(artist)[0])
    x = (WIDTH - tw) // 2
    vector.text(x, y + 34, artist)

    presto.update()
    log("Draw track: {} - {}".format(title, artist))
