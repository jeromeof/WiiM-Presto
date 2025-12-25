# ==========================================================
# Input Handler Module - Touch Button Management
# ==========================================================

from touch import Button
from utils import log

# =======================
# BUTTON DEFINITIONS
# =======================

# Button dimensions (480x480 display)
BUTTON_Y = 390
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 60
BUTTON_SPACING = 30

# Now Playing screen - Playback control buttons
# Centered horizontally: total width = (100*3) + (30*2) = 360px
# Left margin: (480 - 360) / 2 = 60px
prev_button = Button(60, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT)
pause_button = Button(190, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT)
next_button = Button(320, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT)

# Clock screen - Resume button (centered at bottom)
resume_button = Button(140, 400, 200, 70)

# Clock screen - Preset buttons (row above resume button)
# 4 presets in a single row: 90px wide, 50px tall, 20px spacing
PRESET_BUTTON_Y = 330
PRESET_BUTTON_WIDTH = 90
PRESET_BUTTON_HEIGHT = 50
PRESET_BUTTON_SPACING = 20
PRESET_START_X = 30

preset_button_1 = Button(PRESET_START_X, PRESET_BUTTON_Y, PRESET_BUTTON_WIDTH, PRESET_BUTTON_HEIGHT)
preset_button_2 = Button(PRESET_START_X + PRESET_BUTTON_WIDTH + PRESET_BUTTON_SPACING, PRESET_BUTTON_Y, PRESET_BUTTON_WIDTH, PRESET_BUTTON_HEIGHT)
preset_button_3 = Button(PRESET_START_X + (PRESET_BUTTON_WIDTH + PRESET_BUTTON_SPACING) * 2, PRESET_BUTTON_Y, PRESET_BUTTON_WIDTH, PRESET_BUTTON_HEIGHT)
preset_button_4 = Button(PRESET_START_X + (PRESET_BUTTON_WIDTH + PRESET_BUTTON_SPACING) * 3, PRESET_BUTTON_Y, PRESET_BUTTON_WIDTH, PRESET_BUTTON_HEIGHT)

# List of all preset buttons for easy iteration
preset_buttons = [preset_button_1, preset_button_2, preset_button_3, preset_button_4]

# =======================
# BUTTON CHECK FUNCTIONS
# =======================

def check_playback_buttons():
    """
    Check if any playback control buttons are pressed.

    Returns:
        str: "prev", "pause", "next", or None
    """
    log("Checking playback buttons...")

    if prev_button.is_pressed():
        log(">>> Previous button pressed!")
        return "prev"
    elif pause_button.is_pressed():
        log(">>> Pause button pressed!")
        return "pause"
    elif next_button.is_pressed():
        log(">>> Next button pressed!")
        return "next"

    log("No playback button pressed")
    return None


def check_resume_button():
    """
    Check if resume button is pressed.

    Returns:
        bool: True if pressed
    """
    log("Checking resume button...")

    if resume_button.is_pressed():
        log(">>> Resume button pressed!")
        return True

    log("Resume button not pressed")
    return False


def check_screen_tap(presto):
    """
    Check if screen was tapped anywhere (to show buttons).
    Uses presto.touch_a for simple tap detection.

    Args:
        presto: Presto device instance

    Returns:
        bool: True if screen was touched
    """
    # presto.touch_a returns Touch namedtuple (x, y, touched)
    touch_data = presto.touch_a

    log("check_screen_tap() - Touch data: {}".format(touch_data))
    log("check_screen_tap() - Touch data type: {}".format(type(touch_data)))

    if touch_data is None:
        log("check_screen_tap() - touch_data is None!")
        return False

    try:
        # Access the .touched attribute (not index!)
        touch_state = touch_data.touched
        log("check_screen_tap() - Touch state (.touched): {}".format(touch_state))
        log("check_screen_tap() - Touch x: {}, y: {}".format(touch_data.x, touch_data.y))

        if touch_state:
            log(">>> SCREEN TOUCHED! at ({}, {})".format(touch_data.x, touch_data.y))
            return True
        else:
            log("check_screen_tap() - Touch state is False (not touched)")

    except AttributeError as e:
        log("check_screen_tap() - AttributeError: {}".format(e))
        log("check_screen_tap() - Touch data attributes: {}".format(dir(touch_data)))

    return False
