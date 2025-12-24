# ==========================================================
# WiiM Client Module
# ==========================================================

import json
from config import WIIM_IP
from http_client import http_get
from utils import log

def fetch_player_status():
    """
    Fetch current player status from WiiM device.

    Returns:
        dict: Player status data, or None on error
    """
    try:
        raw = http_get(
            "/?ip={}&command=getPlayerStatus".format(WIIM_IP)
        )

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
        raw = http_get(
            "/?ip={}&command=getMetaInfo".format(WIIM_IP)
        )

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
        raw = http_get(
            "/?ip={}&command=setPlayerCmd:{}".format(WIIM_IP, command)
        )

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
