#!/usr/bin/env python3
"""
Roon HTTP Proxy
===============

This proxy server converts Roon's WebSocket API to simple HTTP endpoints
for the MicroPython WiiM display to poll.

Requirements:
    pip install roonapi flask

Setup:
    1. Install dependencies: pip install roonapi flask
    2. Run this script: python3 roon_proxy.py
    3. Go to Roon Settings -> Extensions and authorize this extension
    4. Configure ROON_PROXY_IP in config.py to this machine's IP
    5. The proxy will cache the most recent zone state and serve it via HTTP

Usage:
    python3 roon_proxy.py [--host 0.0.0.0] [--port 9876]

Endpoints:
    GET /status                - Get current playback status (JSON)
    GET /status?zone_id=XXX    - Get status for specific zone
    GET /control/play          - Resume playback
    GET /control/pause         - Pause playback
    GET /control/next          - Next track
    GET /control/previous      - Previous track
    GET /preset/1              - Load preset 1 (configure below)
    GET /image/<image_key>     - Serve album art image
"""

import argparse
import json
import logging
import threading
import time
from flask import Flask, jsonify, request, send_file
from io import BytesIO

try:
    from roonapi import RoonApi, RoonDiscovery
except ImportError:
    print("ERROR: roonapi not installed")
    print("Install with: pip install roonapi")
    exit(1)

# ==========================================================
# CONFIGURATION
# ==========================================================

# Preset mappings: Map preset numbers to Roon actions
# Options:
#   - ("playlist", "playlist_name"): Load a playlist
#   - ("radio", "station_name"): Start radio station
#   - ("tag", "tag_name"): Play from a tag
PRESETS = {
    1: ("radio", "Jazz Radio"),
    2: ("radio", "Classical Radio"),
    3: ("playlist", "Rock Favorites"),
    4: ("radio", "Chill Radio"),
}

# ==========================================================
# GLOBALS
# ==========================================================

app = Flask(__name__)
roon = None
zone_cache = {}  # Cache zone states
image_cache = {}  # Cache album art images
default_zone_id = None

# ==========================================================
# ROON API SETUP
# ==========================================================

def init_roon():
    """Initialize Roon API connection."""
    global roon, default_zone_id

    logging.info("Discovering Roon Core...")
    discover = RoonDiscovery(None)
    servers = discover.all()

    if not servers:
        logging.error("No Roon Core found on network!")
        return False

    server = servers[0]
    logging.info(f"Found Roon Core: {server}")

    # Create API connection
    appinfo = {
        "extension_id": "wiim_display_proxy",
        "display_name": "WiiM Display Proxy",
        "display_version": "1.0.0",
        "publisher": "wiim-display",
        "email": "none@none.com",
    }

    roon = RoonApi(appinfo, server[0], server[1], blocking_init=True)

    # Subscribe to zone changes
    roon.register_state_callback(zone_callback)

    # Get first zone as default
    zones = roon.zones.values()
    if zones:
        default_zone_id = list(zones)[0]["zone_id"]
        logging.info(f"Default zone: {default_zone_id}")

    logging.info("Roon API initialized successfully")
    return True

def zone_callback(event, changed_zones):
    """Callback for zone state changes."""
    global zone_cache

    # Update cache with changed zones
    for zone_id in changed_zones:
        if event == "zones_removed":
            zone_cache.pop(zone_id, None)
        else:
            zone = roon.zones.get(zone_id)
            if zone:
                zone_cache[zone_id] = zone
                logging.debug(f"Updated cache for zone {zone_id}")

# ==========================================================
# HTTP ENDPOINTS
# ==========================================================

@app.route('/status')
def get_status():
    """Get current playback status."""
    zone_id = request.args.get('zone_id', default_zone_id)

    if not zone_id:
        return jsonify({"error": "No zones available"}), 404

    zone = zone_cache.get(zone_id) or roon.zones.get(zone_id)
    if not zone:
        return jsonify({"error": "Zone not found"}), 404

    # Extract relevant info
    state = zone.get("state", "stopped")
    now_playing = zone.get("now_playing", {})

    result = {
        "state": state,
        "zone_id": zone_id,
        "zone_name": zone.get("display_name", "Unknown"),
        "now_playing": now_playing,
        "seek_position": zone.get("seek_position"),
        "settings": zone.get("settings", {}),
    }

    return jsonify(result)

@app.route('/control/play')
def control_play():
    """Resume/start playback."""
    zone_id = request.args.get('zone_id', default_zone_id)
    if not zone_id:
        return jsonify({"error": "No zone"}), 404

    try:
        roon.playback_control(zone_id, "play")
        return jsonify({"ok": True})
    except Exception as e:
        logging.error(f"Play failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/control/pause')
def control_pause():
    """Pause playback."""
    zone_id = request.args.get('zone_id', default_zone_id)
    if not zone_id:
        return jsonify({"error": "No zone"}), 404

    try:
        roon.playback_control(zone_id, "pause")
        return jsonify({"ok": True})
    except Exception as e:
        logging.error(f"Pause failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/control/next')
def control_next():
    """Next track."""
    zone_id = request.args.get('zone_id', default_zone_id)
    if not zone_id:
        return jsonify({"error": "No zone"}), 404

    try:
        roon.playback_control(zone_id, "next")
        return jsonify({"ok": True})
    except Exception as e:
        logging.error(f"Next failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/control/previous')
def control_previous():
    """Previous track."""
    zone_id = request.args.get('zone_id', default_zone_id)
    if not zone_id:
        return jsonify({"error": "No zone"}), 404

    try:
        roon.playback_control(zone_id, "previous")
        return jsonify({"ok": True})
    except Exception as e:
        logging.error(f"Previous failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/preset/<int:preset_num>')
def load_preset(preset_num):
    """Load a preset (playlist, radio, etc.)."""
    zone_id = request.args.get('zone_id', default_zone_id)
    if not zone_id:
        return jsonify({"error": "No zone"}), 404

    if preset_num not in PRESETS:
        return jsonify({"error": "Invalid preset"}), 404

    preset_type, preset_name = PRESETS[preset_num]

    try:
        if preset_type == "radio":
            # Start radio station
            roon.play_radio(zone_id, preset_name)
        elif preset_type == "playlist":
            # Load playlist
            roon.play_playlist(zone_id, preset_name)
        elif preset_type == "tag":
            # Play from tag
            roon.play_tag(zone_id, preset_name)

        return jsonify({"ok": True})
    except Exception as e:
        logging.error(f"Preset {preset_num} failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/image/<image_key>')
def get_image(image_key):
    """Serve album art image."""
    # Check cache
    if image_key in image_cache:
        return send_file(
            BytesIO(image_cache[image_key]),
            mimetype='image/jpeg'
        )

    try:
        # Get image from Roon
        image_data = roon.get_image(image_key)
        if not image_data:
            return "Image not found", 404

        # Cache it
        image_cache[image_key] = image_data

        # Limit cache size (keep last 20 images)
        if len(image_cache) > 20:
            # Remove oldest
            oldest_key = list(image_cache.keys())[0]
            image_cache.pop(oldest_key)

        return send_file(
            BytesIO(image_data),
            mimetype='image/jpeg'
        )
    except Exception as e:
        logging.error(f"Image fetch failed: {e}")
        return "Image error", 500

@app.route('/zones')
def list_zones():
    """List all available zones."""
    zones = []
    for zone_id, zone in roon.zones.items():
        zones.append({
            "zone_id": zone_id,
            "name": zone.get("display_name", "Unknown"),
            "state": zone.get("state", "stopped"),
        })
    return jsonify(zones)

@app.route('/')
def index():
    """Show API documentation."""
    return """
    <html>
    <head><title>Roon HTTP Proxy</title></head>
    <body>
        <h1>Roon HTTP Proxy</h1>
        <p>Proxy for WiiM Display to access Roon API</p>

        <h2>Endpoints:</h2>
        <ul>
            <li><a href="/status">/status</a> - Current playback status</li>
            <li><a href="/zones">/zones</a> - List available zones</li>
            <li>/control/play - Resume playback</li>
            <li>/control/pause - Pause playback</li>
            <li>/control/next - Next track</li>
            <li>/control/previous - Previous track</li>
            <li>/preset/1 - Load preset 1</li>
            <li>/image/&lt;image_key&gt; - Album art</li>
        </ul>

        <h2>Status:</h2>
        <p>Roon: <b>""" + ("Connected" if roon else "Not connected") + """</b></p>
        <p>Zones: <b>""" + str(len(zone_cache)) + """</b></p>
    </body>
    </html>
    """

# ==========================================================
# MAIN
# ==========================================================

def main():
    parser = argparse.ArgumentParser(description="Roon HTTP Proxy for WiiM Display")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9876, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Initialize Roon API
    if not init_roon():
        logging.error("Failed to initialize Roon API")
        return

    # Start Flask server
    logging.info(f"Starting HTTP proxy on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)

if __name__ == "__main__":
    main()
