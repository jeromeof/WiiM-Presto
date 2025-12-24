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

# =======================
# BUTTON CHECK FUNCTIONS
# =======================

def check_playback_buttons():
    """
    Check if any playback control buttons are pressed.

    Returns:
        str: "prev", "pause", "next", or None
    """
    if prev_button.is_pressed():
        log("Previous button pressed")
        return "prev"
    elif pause_button.is_pressed():
        log("Pause button pressed")
        return "pause"
    elif next_button.is_pressed():
        log("Next button pressed")
        return "next"
    return None


def check_resume_button():
    """
    Check if resume button is pressed.

    Returns:
        bool: True if pressed
    """
    if resume_button.is_pressed():
        log("Resume button pressed")
        return True
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
    # presto.touch_a returns (x, y, state) tuple
    # state is True when touched
    touch_data = presto.touch_a
    if touch_data and len(touch_data) >= 3:
        return touch_data[2]  # Return touch state (True/False)
    return False
