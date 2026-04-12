# ==========================================================
# Device Picker UI Module
# Full-screen touch UI for selecting a WiiM device from a
# list of SSDP-discovered devices.
# ==========================================================

import time
from utils import log

# Layout constants
_TITLE_H  = 70
_PAD      = 8
_ITEM_H   = 72
_MAX_ITEMS = 5


def show_device_picker(presto, devices, configured_ip=None):
    """
    Display a device selection screen and wait for a touch.

    Shows up to 5 discovered devices as touch-friendly buttons, plus a
    "Skip" button at the bottom to continue with the configured IP.

    Args:
        presto:        The Presto instance (for display + touch).
        devices:       List of dicts from wiim_discovery: [{"ip":..., "name":...}]
        configured_ip: The IP from secrets.py shown on the Skip button.

    Returns:
        str: IP address of the selected device, or
        None: if Skip was tapped or the 60-second timeout expired.
    """
    display = presto.display
    touch   = presto.touch
    WIDTH, HEIGHT = display.get_bounds()

    # --- Colour palette ---
    BLACK     = display.create_pen(0,   0,   0)
    WHITE     = display.create_pen(255, 255, 255)
    DARK_BLUE = display.create_pen(20,  60,  140)
    ITEM_BG   = display.create_pen(40,  80,  160)
    SKIP_BG   = display.create_pen(55,  55,  55)
    YELLOW    = display.create_pen(255, 200, 0)
    GRAY      = display.create_pen(140, 140, 140)

    visible_devices = devices[:_MAX_ITEMS]

    def _draw():
        display.set_pen(BLACK)
        display.clear()

        # Title bar
        display.set_pen(DARK_BLUE)
        display.rectangle(0, 0, WIDTH, _TITLE_H)
        display.set_pen(WHITE)
        display.text("Select WiiM Device", _PAD, 12, WIDTH - _PAD * 2, 3)
        display.set_pen(GRAY)
        display.text("Tap to connect", _PAD, 46, WIDTH - _PAD * 2, 2)

        if not visible_devices:
            display.set_pen(WHITE)
            display.text("No devices found", _PAD, _TITLE_H + 40, WIDTH - _PAD * 2, 3)
            display.set_pen(GRAY)
            display.text("Using configured IP", _PAD, _TITLE_H + 90, WIDTH - _PAD * 2, 2)

        # Device buttons
        for i, item in enumerate(visible_devices):
            y = _TITLE_H + _PAD + i * (_ITEM_H + _PAD)
            display.set_pen(ITEM_BG)
            display.rectangle(_PAD, y, WIDTH - _PAD * 2, _ITEM_H)

            # Device name (truncate if needed)
            name = item.get("name", "Unknown")
            if len(name) > 22:
                name = name[:22] + "..."
            display.set_pen(WHITE)
            display.text(name, _PAD * 3, y + 10, WIDTH - _PAD * 6, 3)

            # IP address in yellow
            display.set_pen(YELLOW)
            display.text(item["ip"], _PAD * 3, y + 46, WIDTH - _PAD * 6, 2)

        # Skip button pinned to bottom
        skip_y = HEIGHT - _ITEM_H - _PAD
        display.set_pen(SKIP_BG)
        display.rectangle(_PAD, skip_y, WIDTH - _PAD * 2, _ITEM_H)
        display.set_pen(GRAY)
        if configured_ip:
            skip_label = "Skip  (use {})".format(configured_ip)
        else:
            skip_label = "Skip"
        display.text(skip_label, _PAD * 3, skip_y + 22, WIDTH - _PAD * 6, 2)

        presto.update()

    _draw()

    # --- Touch handling (up to 60 seconds) ---
    deadline    = time.ticks_ms() + 60000
    was_touched = False

    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        touch.poll()
        now_touched = touch.state

        # Act on the leading edge of a touch
        if now_touched and not was_touched:
            tx = touch.x
            ty = touch.y

            # Hit-test each device button
            for i, item in enumerate(visible_devices):
                y = _TITLE_H + _PAD + i * (_ITEM_H + _PAD)
                if _PAD <= tx <= WIDTH - _PAD and y <= ty <= y + _ITEM_H:
                    log("Picker: selected {} @ {}".format(
                        item.get("name", "?"), item["ip"]))
                    return item["ip"]

            # Hit-test the Skip button
            skip_y = HEIGHT - _ITEM_H - _PAD
            if _PAD <= tx <= WIDTH - _PAD and skip_y <= ty <= skip_y + _ITEM_H:
                log("Picker: skip pressed")
                return None

        was_touched = now_touched
        time.sleep_ms(50)

    log("Picker: timed out after 60s")
    return None
