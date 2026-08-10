"""
Bharat Voice AI — Weather Tool Tests (Day 5 Specification)

Comprehensive unit and integration tests for WeatherService and BharatVoiceAgent.get_weather:
- Real Geocoding & Forecast lookup for Indian cities (Veraval, Ahmedabad, Mumbai)
- Invalid location handling
- Network timeout, HTTP 500, and API failure handling via mocking
- Memory location fallback when location parameter is blank
- Standardized tool response schema (success, data, error)
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent.voice_agent import BharatVoiceAgent
from services.weather import WeatherService, get_weather_service


@pytest.mark.asyncio
async def test_weather_service_valid_indian_city_veraval() -> None:
    """WeatherService should retrieve live geocoding & forecast for Veraval."""
    service = get_weather_service()
    result = await service.get_weather_data("Veraval")

    assert result["success"] is True
    assert "data" in result
    data = result["data"]

    assert "Ver" in data["location"] or "Veraval" in data["location"]
    assert data["country"] == "India"
    assert isinstance(data["temperature_c"], int)
    assert isinstance(data["humidity_percent"], int)
    assert isinstance(data["precipitation_probability"], int)
    assert data["source"] == "Open-Meteo"


@pytest.mark.asyncio
async def test_weather_service_valid_indian_city_ahmedabad() -> None:
    """WeatherService should retrieve live weather for Ahmedabad."""
    service = get_weather_service()
    result = await service.get_weather_data("Ahmedabad")

    assert result["success"] is True
    assert result["data"]["location"] == "Ahmedabad"
    assert result["data"]["region"] == "Gujarat"


@pytest.mark.asyncio
async def test_weather_service_invalid_location() -> None:
    """WeatherService should return success=False for unknown location."""
    service = get_weather_service()
    result = await service.get_weather_data("XyZ999NonExistentCityName12345")

    assert result["success"] is False
    assert result["error"] == "location_not_found"


@pytest.mark.asyncio
async def test_weather_service_empty_location() -> None:
    """WeatherService should fail gracefully on empty input."""
    service = get_weather_service()
    result = await service.get_weather_data("")

    assert result["success"] is False
    assert result["error"] == "invalid_location"


@pytest.mark.asyncio
async def test_weather_service_timeout_handling() -> None:
    """WeatherService should handle network timeouts cleanly without raising exceptions."""
    service = WeatherService(
        timeout=0.001
    )  # Extremely short timeout to trigger TimeoutException

    with patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.TimeoutException("Connection timed out"),
    ):
        result = await service.get_weather_data("Mumbai")

        assert result["success"] is False
        assert result["error"] == "weather_service_timeout"
        assert "timed out" in result["message"].lower()


@pytest.mark.asyncio
async def test_weather_service_http_500_handling() -> None:
    """WeatherService should handle API 500 server errors cleanly."""
    from unittest.mock import MagicMock

    service = WeatherService()

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="500 Internal Server Error",
        request=httpx.Request("GET", "https://api.open-meteo.com"),
        response=httpx.Response(500),
    )

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await service.get_weather_data("Delhi")

        assert result["success"] is False
        assert result["error"] == "weather_service_unavailable"


@pytest.mark.asyncio
async def test_agent_weather_tool_direct_call() -> None:
    """BharatVoiceAgent.get_weather tool should return valid JSON structure."""
    agent = BharatVoiceAgent(
        session_id="test_weather_session", user_id="test_user_weather"
    )
    context = AsyncMock()

    json_str = await agent.get_weather(context, location="Veraval")
    import json

    data = json.loads(json_str)

    assert data["success"] is True
    assert "Veraval" in data["data"]["location"] or "Ver" in data["data"]["location"]


@pytest.mark.asyncio
async def test_agent_weather_tool_memory_fallback(tmp_path) -> None:
    """If no location is provided, get_weather should infer location from Day 4 saved user profile."""
    agent = BharatVoiceAgent(
        session_id="test_mem_weather_session", user_id="user_rajkot_123"
    )
    context = AsyncMock()

    # Save caller profile with location Rajkot
    agent.db_memory.save_user(
        user_id="user_rajkot_123",
        name="Jayesh",
        language_preference="Gujarati",
        facts={"location": "Rajkot"},
    )

    # Call get_weather without location
    json_str = await agent.get_weather(context, location="")
    import json

    data = json.loads(json_str)

    assert data["success"] is True
    assert data["data"]["location"] == "Rajkot"
