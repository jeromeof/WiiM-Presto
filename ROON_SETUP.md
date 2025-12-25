# Roon Integration Setup

This guide explains how to configure your WiiM Display to work with Roon instead of WiiM.

## Overview

The Roon integration works through an HTTP proxy:

```
┌─────────────────┐        ┌──────────────┐        ┌────────────┐
│  Presto Device  │  HTTP  │  Roon Proxy  │  WSS   │ Roon Core  │
│  (MicroPython)  │ ◄────► │   (Python)   │ ◄────► │  (Server)  │
└─────────────────┘        └──────────────┘        └────────────┘
```

The proxy runs on a computer on your network and converts:
- Roon's WebSocket API → Simple HTTP endpoints for polling
- Image serving through HTTP
- Control commands (play/pause/next/prev)

## Requirements

1. **Roon Core** running on your network
2. **Computer to run proxy** (can be same machine as Roon Core)
   - Python 3.7 or later
   - Network accessible from Presto device
3. **Presto device** with this codebase

## Setup Instructions

### 1. Install Proxy Dependencies

On the computer that will run the proxy:

```bash
pip install roonapi flask
```

### 2. Start the Proxy Server

```bash
python3 roon_proxy.py
```

First run will print:
```
INFO - Discovering Roon Core...
INFO - Found Roon Core: ('192.168.1.100', 9100)
INFO - Roon API initialized successfully
INFO - Default zone: 1e0f8a7b-...
INFO - Starting HTTP proxy on 0.0.0.0:9876
```

### 3. Authorize Extension in Roon

1. Open Roon on your device
2. Go to **Settings** → **Extensions**
3. You should see "**WiiM Display Proxy**" in the list
4. Click **Enable** to authorize it

### 4. Configure Presets (Optional)

Edit `roon_proxy.py` and modify the `PRESETS` dictionary:

```python
PRESETS = {
    1: ("radio", "Jazz Radio"),           # Radio station
    2: ("playlist", "My Classical"),      # Playlist name
    3: ("radio", "Rock Radio"),           # Another radio
    4: ("tag", "Chill"),                  # Tag/genre
}
```

Preset types:
- `"radio"`: Start a Roon Radio station
- `"playlist"`: Load a playlist by name
- `"tag"`: Play from a tag/genre

### 5. Update Presto Configuration

Add these settings to your `config.py`:

```python
# Roon Configuration (instead of WiiM)
USE_ROON = True  # Set to True to use Roon instead of WiiM
ROON_PROXY_IP = "192.168.1.100"  # IP of computer running proxy
ROON_PROXY_PORT = 9876           # Proxy port (default: 9876)
ROON_ZONE_ID = None              # None = auto-detect first zone
                                  # Or specify: "1e0f8a7b-..."
```

### 6. Update main.py Import

Change the import in `main.py` from:

```python
from wiim_client import (
    fetch_player_status, fetch_meta_info,
    pause_playback, resume_playback, next_track, previous_track, load_preset
)
```

To:

```python
# Choose client based on config
from config import USE_ROON

if USE_ROON:
    from roon_client import (
        fetch_player_status, fetch_meta_info,
        pause_playback, resume_playback, next_track, previous_track, load_preset
    )
else:
    from wiim_client import (
        fetch_player_status, fetch_meta_info,
        pause_playback, resume_playback, next_track, previous_track, load_preset
    )
```

### 7. Deploy and Test

1. Upload updated code to Presto:
   ```bash
   # Upload roon_client.py and updated config.py
   ```

2. Restart Presto device

3. Check logs for:
   ```
   [DEBUG] Status: play - Song Title by Artist
   ```

## Testing the Proxy

You can test the proxy directly with a web browser or curl:

```bash
# Get current status
curl http://192.168.1.100:9876/status

# List zones
curl http://192.168.1.100:9876/zones

# Control playback
curl http://192.168.1.100:9876/control/pause
curl http://192.168.1.100:9876/control/play
curl http://192.168.1.100:9876/control/next
```

Or visit `http://192.168.1.100:9876/` in a browser for the status page.

## Advanced Configuration

### Running Proxy as a Service

To run the proxy automatically on startup, create a systemd service:

**File: `/etc/systemd/system/roon-proxy.service`**

```ini
[Unit]
Description=Roon HTTP Proxy
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/WiiM-Presto
ExecStart=/usr/bin/python3 /path/to/WiiM-Presto/roon_proxy.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable roon-proxy
sudo systemctl start roon-proxy
```

### Using Specific Zone

If you have multiple Roon zones and want to use a specific one:

1. Get zone IDs:
   ```bash
   curl http://192.168.1.100:9876/zones
   ```

2. Copy the `zone_id` you want

3. Update `config.py`:
   ```python
   ROON_ZONE_ID = "1e0f8a7b-6c3d-4e5f-a8b9-1234567890ab"
   ```

### Proxy Command Line Options

```bash
# Run on specific port
python3 roon_proxy.py --port 8888

# Bind to specific interface
python3 roon_proxy.py --host 192.168.1.100

# Enable debug logging
python3 roon_proxy.py --debug
```

## Troubleshooting

### Proxy won't connect to Roon Core

**Problem:** "No Roon Core found on network"

**Solutions:**
1. Ensure Roon Core is running
2. Check firewall allows discovery (UDP port 9003)
3. Try manually specifying Roon Core IP in `roon_proxy.py`

### Extension not appearing in Roon

**Problem:** Proxy running but extension doesn't show in Roon Settings

**Solutions:**
1. Restart the proxy
2. Restart Roon Core
3. Check proxy logs for errors

### Presto can't connect to proxy

**Problem:** "Connection failed" in Presto logs

**Solutions:**
1. Verify proxy IP address in `config.py`
2. Check firewall allows HTTP (port 9876)
3. Test with: `curl http://PROXY_IP:9876/status`
4. Ensure both devices on same network

### Album art not loading

**Problem:** Track info shows but no album art

**Solutions:**
1. Check proxy logs: `Image fetch failed`
2. Verify image URLs work: `curl http://PROXY_IP:9876/image/IMAGE_KEY`
3. Check Roon has album art for the track
4. Clear image cache: restart proxy

### Presets not working

**Problem:** Preset buttons do nothing

**Solutions:**
1. Check preset names match exactly (case-sensitive)
2. For playlists: must be exact name as shown in Roon
3. For radio: use station name from Roon
4. Check proxy logs when pressing preset button

## Performance Notes

- **Polling interval:** Uses same intervals as WiiM (10s normal, 1s near track end)
- **Connection pooling:** HTTP connections reused for efficiency
- **Image caching:** Proxy caches last 20 album art images
- **Zone caching:** State cached and updated via Roon callbacks

## API Reference

### Status Response Format

```json
{
  "state": "playing",
  "zone_id": "1e0f8a7b-...",
  "zone_name": "Living Room",
  "seek_position": 45.3,
  "now_playing": {
    "three_line": {
      "line1": "Song Title",
      "line2": "Artist Name",
      "line3": "Album Name"
    },
    "length": 245,
    "image_key": "abc123..."
  }
}
```

### Control Endpoints

- `GET /status` - Current playback status
- `GET /status?zone_id=XXX` - Status for specific zone
- `GET /control/play` - Resume playback
- `GET /control/pause` - Pause playback
- `GET /control/next` - Skip to next track
- `GET /control/previous` - Previous track
- `GET /preset/N` - Load preset N (1-4)
- `GET /image/<key>` - Get album art image
- `GET /zones` - List all zones

## License

Same as main project.
