# ==========================================================
# Music Client Adapter
# ==========================================================
#
# This module provides a unified interface for both WiiM and Roon.
# Import from this module instead of directly from wiim_client or roon_client.
#
# Usage in main.py:
#   from music_client import (
#       fetch_player_status, fetch_meta_info,
#       pause_playback, resume_playback, next_track, previous_track, load_preset
#   )

from config import USE_ROON

if USE_ROON:
    # Import Roon client
    from roon_client import (
        fetch_player_status,
        fetch_meta_info,
        pause_playback,
        resume_playback,
        next_track,
        previous_track,
        load_preset,
        test_connection
    )
    print("Music client: Using Roon")

    # Roon doesn't support WiiM-style presets
    def fetch_presets():
        return None

else:
    # Import WiiM client
    from wiim_client import (
        fetch_player_status,
        fetch_meta_info,
        pause_playback,
        resume_playback,
        next_track,
        previous_track,
        load_preset,
        fetch_presets
    )
    print("Music client: Using WiiM")

    # WiiM doesn't have test_connection, provide stub
    def test_connection():
        return True

# Re-export all functions
__all__ = [
    'fetch_player_status',
    'fetch_meta_info',
    'pause_playback',
    'resume_playback',
    'next_track',
    'previous_track',
    'load_preset',
    'fetch_presets',
    'test_connection'
]
