"""
Bharat Voice AI — Weather Service

Real-time weather data service powered by Open-Meteo API.
Provides geocoding resolution and forecast retrieval with robust error handling,
timeouts, input validation, and WMO weather code interpretation.
"""

import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger("bharat_voice_ai.weather")

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 5.0

# WMO Weather Interpretation Codes (WW) mapping to natural condition text
WMO_WEATHER_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherService:
    """Service wrapper for Open-Meteo Geocoding & Weather Forecast REST APIs."""

    def __init__(self, timeout: float = REQUEST_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout

    async def get_weather_data(
        self, location: str, forecast_days: int = 1
    ) -> dict[str, Any]:
        """
        Fetch current and forecast weather data for a location.

        Args:
            location: Name of the city/region (e.g. 'Veraval', 'Ahmedabad', 'Mumbai').
            forecast_days: Number of forecast days to retrieve (1 to 7).

        Returns:
            Structured dictionary with 'success': True and 'data' dict, or 'success': False and 'error'.
        """
        clean_location = location.strip() if location else ""
        if not clean_location or len(clean_location) < 2:
            logger.warning(
                "[WEATHER SERVICE] Invalid or empty location provided: '%s'", location
            )
            return {
                "success": False,
                "error": "invalid_location",
                "message": "Location name must be at least 2 characters long.",
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Step 1: Geocoding Resolution
                logger.info(
                    "[WEATHER SERVICE] Geocoding request for location '%s'",
                    clean_location,
                )
                geo_resp = await client.get(
                    GEOCODING_URL,
                    params={
                        "name": clean_location,
                        "count": 5,
                        "language": "en",
                        "format": "json",
                    },
                )
                geo_resp.raise_for_status()
                geo_data = geo_resp.json()

                results = geo_data.get("results")
                if not results:
                    logger.warning(
                        "[WEATHER SERVICE] Location not found in Open-Meteo geocoding: '%s'",
                        clean_location,
                    )
                    return {
                        "success": False,
                        "error": "location_not_found",
                        "message": f"Could not find coordinates for location: '{clean_location}'.",
                    }

                # Prefer Indian match if available, otherwise take first result
                target_place = results[0]
                for place in results:
                    if place.get("country_code") == "IN":
                        target_place = place
                        break

                lat = target_place.get("latitude")
                lon = target_place.get("longitude")
                display_name = target_place.get("name", clean_location)
                admin1 = target_place.get("admin1", "")
                country = target_place.get("country", "India")
                timezone = target_place.get("timezone", "Asia/Kolkata")

                # Step 2: Fetch Forecast Data
                logger.info(
                    "[WEATHER SERVICE] Fetching forecast for '%s' (lat=%.4f, lon=%.4f)",
                    display_name,
                    lat,
                    lon,
                )
                forecast_resp = await client.get(
                    FORECAST_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": (
                            "temperature_2m,relative_humidity_2m,apparent_temperature,"
                            "precipitation,rain,weather_code,wind_speed_10m"
                        ),
                        "daily": (
                            "weather_code,temperature_2m_max,temperature_2m_min,"
                            "precipitation_probability_max"
                        ),
                        "timezone": timezone,
                    },
                )
                forecast_resp.raise_for_status()
                weather_info = forecast_resp.json()

                current = weather_info.get("current", {})
                daily = weather_info.get("daily", {})

                # Interpret Weather Code
                weather_code = current.get("weather_code", 0)
                condition_text = WMO_WEATHER_CODES.get(weather_code, "Partly cloudy")

                # Extract daily precipitation probability
                daily_probs = daily.get("precipitation_probability_max", [])
                precip_prob = (
                    daily_probs[0]
                    if daily_probs
                    else int(current.get("precipitation", 0) > 0) * 50
                )

                result_data = {
                    "location": display_name,
                    "region": admin1,
                    "country": country,
                    "temperature_c": round(current.get("temperature_2m", 0)),
                    "feels_like_c": round(current.get("apparent_temperature", 0)),
                    "condition": condition_text,
                    "humidity_percent": current.get("relative_humidity_2m", 0),
                    "precipitation_probability": precip_prob,
                    "wind_kmh": round(current.get("wind_speed_10m", 0)),
                    "forecast_date": daily.get("time", [str(datetime.now().date())])[0],
                    "source": "Open-Meteo",
                    "retrieved_at": datetime.now().isoformat(),
                }

                logger.info(
                    "[WEATHER SERVICE] Successfully fetched weather for '%s': %d°C, %s",
                    display_name,
                    result_data["temperature_c"],
                    condition_text,
                )

                return {
                    "success": True,
                    "data": result_data,
                }

        except httpx.TimeoutException:
            logger.error(
                "[WEATHER SERVICE] Timeout fetching weather data for '%s'",
                clean_location,
            )
            return {
                "success": False,
                "error": "weather_service_timeout",
                "message": f"Weather API timed out while checking location '{clean_location}'.",
            }
        except httpx.HTTPError as exc:
            logger.error(
                "[WEATHER SERVICE] HTTP error fetching weather for '%s': %s",
                clean_location,
                str(exc),
            )
            return {
                "success": False,
                "error": "weather_service_unavailable",
                "message": "Live weather service is currently unavailable.",
            }
        except Exception as exc:
            logger.error(
                "[WEATHER SERVICE] Unexpected error fetching weather for '%s': %s",
                clean_location,
                str(exc),
            )
            return {
                "success": False,
                "error": "weather_service_error",
                "message": f"Unexpected weather service error: {exc!s}",
            }


# Singleton service instance
_weather_service = WeatherService()


def get_weather_service() -> WeatherService:
    """Get singleton WeatherService instance."""
    return _weather_service
