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

# Clock screen - Preset buttons (vertical list, dynamically built)
# Rebuilt by display_manager when preset labels are known
PRESET_BUTTON_START_Y = 20   # Top of first button
PRESET_BUTTON_HEIGHT = 70    # Tall enough for easy tapping
PRESET_BUTTON_GAP = 12       # Gap between buttons
PRESET_BUTTON_MARGIN_X = 20  # Left margin

# Populated by rebuild_preset_buttons(); both lists are parallel.
preset_buttons = []         # Button objects (touch areas)
preset_button_numbers = []  # Corresponding WiiM preset numbers (1-based)


def rebuild_preset_buttons(labels, button_width):
    """
    Rebuild preset button touch areas for a vertical layout.
    Only creates buttons for non-None labels.
    Stores the original WiiM preset number alongside each button.

    Args:
        labels: List of 4 label strings (None = slot unused), index 0 = preset 1
        button_width: Width in pixels for each button
    """
    global preset_buttons, preset_button_numbers
    preset_buttons = []
    preset_button_numbers = []
    y = PRESET_BUTTON_START_Y
    for wiim_num, label in enumerate(labels, start=1):
        if label is not None:
            preset_buttons.append(
                Button(PRESET_BUTTON_MARGIN_X, y, button_width, PRESET_BUTTON_HEIGHT)
            )
            preset_button_numbers.append(wiim_num)
            y += PRESET_BUTTON_HEIGHT + PRESET_BUTTON_GAP
    log("Rebuilt {} preset buttons (width={})".format(len(preset_buttons), button_width))

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
