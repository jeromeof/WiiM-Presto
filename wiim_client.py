# ==========================================================
# WiiM Client Module
# ==========================================================

import json
from config import WIIM_IP, USE_PROXY
from http_client import http_get
from utils import log

def _build_path(command):
    """
    Build API path for WiiM command.

    Args:
        command: WiiM API command (e.g., getPlayerStatus, getMetaInfo)

    Returns:
        str: Full path for the request
    """
    if USE_PROXY:
        # Proxy mode: router forwards to WiiM based on ip parameter
        return "/?ip={}&command={}".format(WIIM_IP, command)
    else:
        # Direct mode: use WiiM's native API endpoint
        return "/httpapi.asp?command={}".format(command)

def fetch_player_status():
    """
    Fetch current player status from WiiM device.

    Returns:
        dict: Player status data, or None on error
    """
    try:
        raw = http_get(_build_path("getPlayerStatus"))

        if not raw:
            log("Empty HTTP response")
            return None

        # Find start of JSON
        start = raw.find(b"{")
        if start < 0:
            log("No JSON found in response")
            return None

        body = raw[start:].rstrip(b"% \r\n")

        return json.loads(body)

    except Exception as e:
        log("Playback error: {}".format(e))
        return None

def fetch_meta_info():
    """
    Fetch metadata information from WiiM device.
    Includes album art URL and other track details.

    Returns:
        dict: Metadata, or None on error
    """
    try:
        raw = http_get(_build_path("getMetaInfo"))

        if not raw:
            log("MetaInfo empty response")
            return None

        start = raw.find(b"{")
        if start < 0:
            log("MetaInfo no JSON")
            return None

        body = raw[start:].rstrip(b"% \r\n")
        data = json.loads(body)

        return data.get("metaData")

    except Exception as e:
        log("MetaInfo error: {}".format(e))
        return None

def send_player_command(command):
    """
    Send playback control command to WiiM device.

    Args:
        command: Control command (pause, resume, next, prev)

    Returns:
        bool: True if command succeeded (response contains "OK")
    """
    try:
        raw = http_get(_build_path("setPlayerCmd:{}".format(command)))

        if not raw:
            log("Control command failed: empty response")
            return False

        # Check if response contains "OK"
        if b"OK" in raw:
            log("Control command succeeded: {}".format(command))
            return True
        else:
            log("Control command failed: {}".format(command))
            return False

    except Exception as e:
        log("Control error: {}".format(e))
        return False


def pause_playback():
    """Pause current playback."""
    return send_player_command("pause")


def resume_playback():
    """Resume paused playback."""
    return send_player_command("resume")


def next_track():
    """Skip to next track."""
    return send_player_command("next")


def previous_track():
    """Go to previous track."""
    return send_player_command("prev")


def load_preset(preset_number):
    """
    Load a WiiM preset (1-4).

    Args:
        preset_number: Preset number (1-4)

    Returns:
        bool: True if command succeeded
    """
    if preset_number < 1 or preset_number > 4:
        log("Invalid preset number: {}".format(preset_number))
        return False

    try:
        # WiiM preset command format: MCUKeyShortClick:N
        raw = http_get(_build_path("MCUKeyShortClick:{}".format(preset_number)))

        if not raw:
            log("Preset {} command failed: empty response".format(preset_number))
            return False

        # Check if response contains "OK"
        if b"OK" in raw:
            log("Preset {} loaded successfully".format(preset_number))
            return True
        else:
            log("Preset {} command failed".format(preset_number))
            return False

    except Exception as e:
        log("Preset error: {}".format(e))
        return False
