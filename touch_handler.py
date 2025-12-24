# ==========================================================
# Touch Handler Module - Background Touch Detection
# ==========================================================

import uasyncio as asyncio
import time
from utils import log

class TouchHandler:
    """
    Manages touch detection in a background async task.
    Can be enabled/disabled without affecting main loop.
    """

    def __init__(self, presto):
        """
        Initialize touch handler.

        Args:
            presto: Presto device instance
        """
        self.presto = presto
        self.touch = presto.touch
        self.enabled = False
        self.task = None

        # Touch state
        self.screen_touched = False
        self.last_touch_x = 0
        self.last_touch_y = 0
        self.last_touch_time = 0

        # Button state
        self.buttons_visible = False
        self.button_timeout_ms = 5000
        self.last_button_show_time = 0

        log("TouchHandler initialized")

    def enable(self):
        """Enable touch detection - starts background polling."""
        if not self.enabled:
            self.enabled = True
            log("TouchHandler ENABLED")
            if self.task is None:
                self.task = asyncio.create_task(self._poll_loop())

    def disable(self):
        """Disable touch detection - stops background polling."""
        if self.enabled:
            self.enabled = False
            log("TouchHandler DISABLED")

    def reset_touch_state(self):
        """Clear current touch state."""
        self.screen_touched = False
        self.last_touch_x = 0
        self.last_touch_y = 0

    def was_screen_touched(self):
        """
        Check if screen was touched since last check.
        Clears the touch flag after checking.

        Returns:
            bool: True if screen was touched
        """
        if self.screen_touched:
            log("TouchHandler: Screen touch consumed")
            self.screen_touched = False
            return True
        return False

    def get_last_touch_coords(self):
        """
        Get coordinates of last touch.

        Returns:
            tuple: (x, y) coordinates
        """
        return (self.last_touch_x, self.last_touch_y)

    def check_button_press(self, button):
        """
        Check if a specific button was pressed.

        Args:
            button: Button object to check

        Returns:
            bool: True if button is pressed
        """
        if not self.enabled:
            return False

        return button.is_pressed()

    def show_buttons(self):
        """Show buttons and reset timeout."""
        self.buttons_visible = True
        self.last_button_show_time = time.ticks_ms()
        log("TouchHandler: Buttons shown")

    def hide_buttons(self):
        """Hide buttons."""
        self.buttons_visible = False
        log("TouchHandler: Buttons hidden")

    def are_buttons_visible(self):
        """Check if buttons should be visible."""
        if not self.buttons_visible:
            return False

        # Check timeout
        elapsed = time.ticks_diff(time.ticks_ms(), self.last_button_show_time)
        if elapsed > self.button_timeout_ms:
            log("TouchHandler: Button timeout ({}ms)".format(elapsed))
            self.hide_buttons()
            return False

        return True

    async def _poll_loop(self):
        """
        Background polling loop for touch detection.
        Runs continuously when enabled.
        """
        log("TouchHandler: Polling loop started")

        while True:
            if self.enabled:
                # Poll touch
                self.touch.poll()
                touch_a = self.presto.touch_a

                # Check for touch
                if touch_a and touch_a.touched:
                    self.screen_touched = True
                    self.last_touch_x = touch_a.x
                    self.last_touch_y = touch_a.y
                    self.last_touch_time = time.ticks_ms()

                    log("TouchHandler: Touch detected at ({}, {})".format(
                        touch_a.x, touch_a.y
                    ))

                # Poll every 50ms when enabled
                await asyncio.sleep_ms(50)
            else:
                # When disabled, check less frequently
                await asyncio.sleep_ms(500)
