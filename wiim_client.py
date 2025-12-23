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
