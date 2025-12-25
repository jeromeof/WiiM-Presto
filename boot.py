# ==========================================================
# Boot Script for Pimoroni Presto
# Runs automatically on power-up
# ==========================================================

import gc
import sys

# Enable garbage collection
gc.enable()

# Print boot message (visible in REPL if connected)
print("Presto boot.py starting...")

# Set up sys path if needed
sys.path.append('')

# Disable REPL on UART if needed to save resources
# (Only do this if you don't need serial debugging)
# import uos
# uos.dupterm(None, 1)

print("Boot complete, starting main.py...")

# main.py will run automatically after this
