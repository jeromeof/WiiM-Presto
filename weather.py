# ==========================================================
# Weather Module for MicroPython
# Simplified version using OpenWeatherMap API
# ==========================================================

import time
import json
import urequests as requests
from config import WEATHER_API_KEY, WEATHER_LOCATION, WEATHER_UNITS, WEATHER_CACHE_TIME
from utils import log

# In-memory cache
_weather_cache = {
    "data": None,
    "timestamp": 0
}

def get_weather():
    """
    Fetch current weather from OpenWeatherMap API.
    Returns dict with temperature, description, and location.
    Uses caching to reduce API calls.
    """
    global _weather_cache

    # Check cache validity
    cache_age = time.time() - _weather_cache["timestamp"]
    if _weather_cache["data"] and cache_age < WEATHER_CACHE_TIME:
        log("Using cached weather (age: {}s)".format(int(cache_age)))
        return _weather_cache["data"]

    # Fetch fresh data
    try:
        log("Fetching weather from OpenWeatherMap")

        url = "http://api.openweathermap.org/data/2.5/weather"
        params = "?q={}&appid={}&units={}".format(
            WEATHER_LOCATION,
            WEATHER_API_KEY,
            WEATHER_UNITS
        )

        response = requests.get(url + params, timeout=10)

        if response.status_code != 200:
            log("Weather API error: {}".format(response.status_code))
            response.close()
            return None

        data = response.json()
        response.close()

        # Extract relevant info
        temp = data["main"]["temp"]
        description = data["weather"][0]["description"]
        location = data["name"]

        # Format temperature
        temp_unit = "C" if WEATHER_UNITS == "metric" else "F"

        # Capitalize description (title() may not exist in MicroPython)
        desc_formatted = description[0].upper() + description[1:] if description else ""

        weather_info = {
            "temperature": "{:.0f}°{}".format(temp, temp_unit),
            "description": desc_formatted,
            "location": location
        }

        # Update cache
        _weather_cache["data"] = weather_info
        _weather_cache["timestamp"] = time.time()

        log("Weather: {} {}".format(weather_info["temperature"], weather_info["description"]))
        return weather_info

    except Exception as e:
        log("Weather fetch error: {}".format(e))
        return None

def clear_cache():
    """Clear the weather cache to force a fresh fetch."""
    global _weather_cache
    _weather_cache["data"] = None
    _weather_cache["timestamp"] = 0
    log("Weather cache cleared")
