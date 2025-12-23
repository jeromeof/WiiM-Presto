# ==========================================================
# Utility Functions Module
# ==========================================================

from config import DEBUG

# =======================
# LOGGING
# =======================

def log(msg):
    """Log a debug message if DEBUG mode is enabled."""
    if DEBUG:
        print("[DEBUG]", msg)

# =======================
# HEX DECODING
# =======================

def hex_to_text(val):
    """
    Convert hex-encoded string to UTF-8 text.
    Used for decoding WiiM metadata fields.
    """
    if not val:
        return ""
    try:
        return bytes.fromhex(val).decode("utf-8", "replace")
    except Exception:
        return ""
