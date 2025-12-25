# ==========================================================
# Touch Manager Module - Unified Touch Handling
# ==========================================================

import uasyncio as asyncio
import time
from utils import log
from input_handler import prev_button, pause_button, next_button, resume_button

class TouchManager:
    """
    Unified touch management - handles all touch detection and button logic.
    """

    def __init__(self, presto):
        """Initialize touch manager."""
        self.presto = presto
        self.touch = presto.touch
        self.enabled = False
        self.task = None

        # Touch state
        self.screen_touched = False
        self.last_touch_x = 0
        self.last_touch_y = 0
        self.last_touch_time = 0

        # Button visibility
        self.playback_buttons_visible = False
        self.resume_button_visible = False
        self.button_timeout_ms = 10000  # 10 seconds
        self.last_button_show_time = 0
        self.last_resume_button_show_time = 0

        log("TouchManager initialized")

    def enable(self):
        """Enable touch detection."""
        if not self.enabled:
            self.enabled = True
            log("TouchManager ENABLED")
            if self.task is None:
                self.task = asyncio.create_task(self._poll_loop())

    def disable(self):
        """Disable touch detection."""
        if self.enabled:
            self.enabled = False
            log("TouchManager DISABLED")

    async def _poll_loop(self):
        """Background touch polling loop."""
        log("TouchManager: Polling loop started")

        while True:
            if self.enabled:
                self.touch.poll()
                touch_a = self.presto.touch_a

                if touch_a and touch_a.touched:
                    self.screen_touched = True
                    self.last_touch_x = touch_a.x
                    self.last_touch_y = touch_a.y
                    self.last_touch_time = time.ticks_ms()

                    log("TouchManager: Touch at ({}, {})".format(
                        touch_a.x, touch_a.y
                    ))

                await asyncio.sleep_ms(50)  # Poll every 50ms
            else:
                await asyncio.sleep_ms(500)  # Sleep longer when disabled

    def was_touched(self):
        """
        Check if screen was touched and consume the event.
        Returns: (touched, x, y)
        """
        if self.screen_touched:
            self.screen_touched = False
            return (True, self.last_touch_x, self.last_touch_y)
        return (False, 0, 0)

    def is_touch_in_button(self, x, y, button):
        """Check if coordinates are inside button bounds."""
        bx, by, bw, bh = button.bounds
        return (bx <= x < bx + bw) and (by <= y < by + bh)

    def handle_touch_on_playing_screen(self):
        """
        Handle touch on Now Playing screen.
        Returns: ("show_buttons", "hide_buttons", "prev", "pause", "next", None)
        """
        touched, x, y = self.was_touched()
        if not touched:
            # Check for button timeout
            if self.playback_buttons_visible:
                elapsed = time.ticks_diff(time.ticks_ms(), self.last_button_show_time)
                if elapsed > self.button_timeout_ms:
                    log("TouchManager: Button timeout")
                    self.playback_buttons_visible = False
                    return "hide_buttons"
            return None

        log("TouchManager: Touch on playing screen at ({}, {})".format(x, y))

        # Check if touch is in button area
        in_prev = self.is_touch_in_button(x, y, prev_button)
        in_pause = self.is_touch_in_button(x, y, pause_button)
        in_next = self.is_touch_in_button(x, y, next_button)
        in_any_button = in_prev or in_pause or in_next

        if self.playback_buttons_visible:
            # Buttons visible - check what was touched
            if in_prev:
                log("TouchManager: PREV button touched")
                self.playback_buttons_visible = False
                return "prev"
            elif in_pause:
                log("TouchManager: PAUSE button touched")
                self.playback_buttons_visible = False
                return "pause"
            elif in_next:
                log("TouchManager: NEXT button touched")
                self.playback_buttons_visible = False
                return "next"
            else:
                # Touch outside buttons - hide them
                log("TouchManager: Touch outside buttons - hiding")
                self.playback_buttons_visible = False
                return "hide_buttons"
        else:
            # Buttons hidden - show them
            log("TouchManager: Showing playback buttons")
            self.playback_buttons_visible = True
            self.last_button_show_time = time.ticks_ms()
            return "show_buttons"

    def handle_touch_on_clock_screen(self):
        """
        Handle touch on Clock screen (paused/stopped).
        Returns: ("show_buttons", "hide_buttons", "resume", "preset_1", "preset_2", "preset_3", "preset_4", None)
        """
        from input_handler import preset_buttons

        touched, x, y = self.was_touched()
        if not touched:
            # Check for button timeout
            if self.resume_button_visible:
                elapsed = time.ticks_diff(time.ticks_ms(), self.last_resume_button_show_time)
                if elapsed > self.button_timeout_ms:
                    log("TouchManager: Clock buttons timeout")
                    self.resume_button_visible = False
                    return "hide_buttons"
            return None

        log("TouchManager: Touch on clock screen at ({}, {})".format(x, y))

        # Check if touch is in any button area
        in_resume = self.is_touch_in_button(x, y, resume_button)
        in_preset = None
        for i, preset_btn in enumerate(preset_buttons):
            if self.is_touch_in_button(x, y, preset_btn):
                in_preset = i + 1  # Preset number (1-4)
                break

        if self.resume_button_visible:
            # Resume button already visible
            if in_resume:
                # Touched resume button - execute resume
                log("TouchManager: RESUME button touched")
                self.resume_button_visible = False
                return "resume"
            elif in_preset:
                # Touched preset button (if presets are visible)
                log("TouchManager: PRESET {} button touched".format(in_preset))
                self.resume_button_visible = False
                return "preset_{}".format(in_preset)
            else:
                # Touch outside resume button - show preset buttons too
                log("TouchManager: Touch outside resume - showing presets")
                return "show_presets"
        else:
            # No buttons visible - show resume button only on first touch
            log("TouchManager: Showing resume button")
            self.resume_button_visible = True
            self.last_resume_button_show_time = time.ticks_ms()
            return "show_resume"

    def are_playback_buttons_visible(self):
        """Check if playback buttons should be visible."""
        return self.playback_buttons_visible

    def is_resume_button_visible(self):
        """Check if resume button should be visible."""
        return self.resume_button_visible

    def hide_playback_buttons(self):
        """Hide playback buttons."""
        self.playback_buttons_visible = False
        log("TouchManager: Playback buttons hidden")

    def hide_resume_button(self):
        """Hide resume button."""
        self.resume_button_visible = False
        log("TouchManager: Resume button hidden")

    def show_resume_button(self):
        """Show resume button and start timeout timer."""
        import time
        self.resume_button_visible = True
        self.last_resume_button_show_time = time.ticks_ms()
        log("TouchManager: Resume button shown")
