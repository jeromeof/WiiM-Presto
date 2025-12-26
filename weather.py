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

        full_url = url + params
        log("Weather URL: {}".format(full_url[:60] + "..."))  # Don't log full API key

        response = requests.get(full_url, timeout=10)

        log("Weather response status: {}".format(response.status_code))

        if response.status_code != 200:
            log("Weather API error: {} - {}".format(response.status_code, response.text[:100]))
            response.close()
            return None

        data = response.json()
        log("Weather data received: {}".format(str(data)[:100]))
        response.close()

        # Extract relevant info
        temp = data["main"]["temp"]
        description = data["weather"][0]["description"]
        location = data["name"]
        
        # Check for rain (likelihood or current)
        # OWM current weather doesn't have 'pop', but may have 'rain'
        # Forecast has 'pop'. Let's check for 'pop' in case it's there or just use rain volume.
        rain_info = None
        if "rain" in data:
            if "1h" in data["rain"]:
                rain_info = "Rain: {}mm".format(data["rain"]["1h"])
            elif "3h" in data["rain"]:
                rain_info = "Rain: {}mm".format(data["rain"]["3h"])
        
        # Also check for clouds as a fallback for "likelihood" if no rain field
        clouds = data.get("clouds", {}).get("all", 0)
        
        # Format temperature
        temp_unit = "C" if WEATHER_UNITS == "metric" else "F"

        # Capitalize description (title() may not exist in MicroPython)
        desc_formatted = description[0].upper() + description[1:] if description else ""

        weather_info = {
            "temperature": "{:.0f}°{}".format(temp, temp_unit),
            "description": desc_formatted,
            "location": location,
            "rain": rain_info,
            "clouds": clouds
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
