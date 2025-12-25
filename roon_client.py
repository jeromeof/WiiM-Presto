# ==========================================================
# Roon Client Module (via HTTP Proxy)
# ==========================================================
#
# This module communicates with a Roon Core via an HTTP proxy.
# The proxy converts Roon's WebSocket API to simple HTTP endpoints.
#
# Requirements:
#   - Roon Core running on your network
#   - roon_proxy.py running (see roon_proxy.py for setup)
#   - Configure ROON_PROXY_IP and ROON_PROXY_PORT in config.py

import json
from http_client import http_get, close_connection
from utils import log

# Import configuration
try:
    from config import ROON_PROXY_IP, ROON_PROXY_PORT, ROON_ZONE_ID
except ImportError:
    # Fallback defaults
    ROON_PROXY_IP = "192.168.1.100"
    ROON_PROXY_PORT = 9876
    ROON_ZONE_ID = None  # Auto-detect first zone

def _build_path(endpoint):
    """Build HTTP path for Roon proxy request."""
    if ROON_ZONE_ID:
        return "http://{}:{}/{}?zone_id={}".format(
            ROON_PROXY_IP, ROON_PROXY_PORT, endpoint, ROON_ZONE_ID
        )
    else:
        return "http://{}:{}/{}".format(ROON_PROXY_IP, ROON_PROXY_PORT, endpoint)

def _parse_json(raw_data):
    """
    Extract and parse JSON from HTTP response.

    Args:
        raw_data: Raw HTTP response bytes

    Returns:
        dict: Parsed JSON data or None if parsing fails
    """
    if not raw_data:
        return None

    try:
        # Find JSON body (after headers)
        sep = raw_data.find(b"\r\n\r\n")
        if sep < 0:
            log("No HTTP body found")
            return None

        json_data = raw_data[sep + 4:].decode('utf-8').strip()
        if not json_data:
            log("Empty response body")
            return None

        return json.loads(json_data)
    except Exception as e:
        log("JSON parse error: {}".format(e))
        return None

def fetch_player_status():
    """
    Fetch current playback status from Roon.

    Returns:
        dict: Player status with keys:
            - status: "play", "pause", or "stop"
            - Title: Track title (hex encoded)
            - Artist: Artist name (hex encoded)
            - Album: Album name (hex encoded)
            - totlen: Total track length in milliseconds
            - curpos: Current position in milliseconds
        None if request fails
    """
    try:
        raw = http_get(_build_path("status"))
        data = _parse_json(raw)

        if not data:
            log("Status fetch failed")
            return None

        # Check if zone is playing
        state = data.get("state", "stopped")

        # Convert Roon state to WiiM-compatible format
        if state == "playing":
            status = "play"
        elif state == "paused":
            status = "pause"
        else:
            status = "stop"

        # Extract track info
        now_playing = data.get("now_playing", {})
        three_line = now_playing.get("three_line", {})

        title = three_line.get("line1", "Unknown")
        artist = three_line.get("line2", "Unknown Artist")
        album = three_line.get("line3", "")

        # Hex encode strings (for compatibility with WiiM format)
        def text_to_hex(text):
            if not text:
                return ""
            return text.encode('utf-8').hex()

        # Get timing info
        seek_position = data.get("seek_position")  # seconds
        length = now_playing.get("length")  # seconds

        result = {
            "status": status,
            "Title": text_to_hex(title),
            "Artist": text_to_hex(artist),
            "Album": text_to_hex(album),
            "totlen": int(length * 1000) if length else 0,  # Convert to ms
            "curpos": int(seek_position * 1000) if seek_position else 0,  # Convert to ms
        }

        log("Status: {} - {} by {}".format(status, title[:30], artist[:30]))
        return result

    except Exception as e:
        log("fetch_player_status error: {}".format(e))
        return None

def fetch_meta_info():
    """
    Fetch track metadata including album art URL.

    Returns:
        dict: Metadata with keys:
            - albumArtURI: URL to album art image
        None if request fails
    """
    try:
        raw = http_get(_build_path("status"))
        data = _parse_json(raw)

        if not data:
            log("Metadata fetch failed")
            return None

        now_playing = data.get("now_playing", {})
        image_key = now_playing.get("image_key")

        if not image_key:
            log("No album art available")
            return {"albumArtURI": None}

        # Build album art URL (proxy serves images)
        art_url = "http://{}:{}/image/{}".format(
            ROON_PROXY_IP, ROON_PROXY_PORT, image_key
        )

        log("Album art: {}".format(art_url[:50]))
        return {"albumArtURI": art_url}

    except Exception as e:
        log("fetch_meta_info error: {}".format(e))
        return None

def send_player_command(command):
    """
    Send a control command to Roon.

    Args:
        command: Command string ("play", "pause", "next", "prev")

    Returns:
        bool: True if successful
    """
    try:
        raw = http_get(_build_path("control/{}".format(command)))

        if not raw or b'"ok"' not in raw.lower():
            log("Control command failed: {}".format(command))
            return False

        log("Control command succeeded: {}".format(command))
        # Close connection after control commands to avoid stale connections
        close_connection()
        return True

    except Exception as e:
        log("send_player_command error: {}".format(e))
        close_connection()
        return False

def pause_playback():
    """Pause current playback."""
    return send_player_command("pause")

def resume_playback():
    """Resume playback (play/unpause)."""
    return send_player_command("play")

def next_track():
    """Skip to next track."""
    return send_player_command("next")

def previous_track():
    """Go to previous track."""
    return send_player_command("previous")

def load_preset(preset_number):
    """
    Load a Roon preset (playlist, radio station, etc.).

    Note: This requires configuring presets in the proxy.
    The proxy maps preset numbers to Roon playlist/radio URIs.

    Args:
        preset_number: Preset number (1-4)

    Returns:
        bool: True if successful
    """
    try:
        raw = http_get(_build_path("preset/{}".format(preset_number)))

        if not raw or b'"ok"' not in raw.lower():
            log("Preset load failed: {}".format(preset_number))
            return False

        log("Preset loaded: {}".format(preset_number))
        close_connection()
        return True

    except Exception as e:
        log("load_preset error: {}".format(e))
        close_connection()
        return False

def test_connection():
    """
    Test connection to Roon proxy.

    Returns:
        bool: True if connection successful
    """
    log("=" * 50)
    log("Testing Roon proxy connection")
    log("=" * 50)
    log("Proxy: {}:{}".format(ROON_PROXY_IP, ROON_PROXY_PORT))

    status = fetch_player_status()
    if status:
        log("SUCCESS! Connected to Roon")
        return True
    else:
        log("FAILED - Cannot connect to Roon proxy")
        return False
