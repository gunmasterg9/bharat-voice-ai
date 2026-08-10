# Day 5 Architecture & Tool Reference — Real-Time Weather Lookup

## 1. Architectural Sequence Flow

```
User (Voice Query)
      │
      ▼
Speech-to-Text (Deepgram Nova-3)
      │ Transcribed Text (e.g., "What's the weather in Veraval today?")
      ▼
LLM Orchestrator (Google Gemini)
      │ Evaluates query & recognizes live weather intent
      ├── Invokes Tool: `get_weather(location="Veraval")`
      ▼
Agent Tool (`backend/src/agent/voice_agent.py`)
      │ Checked Day 4 persistent memory if location missing
      ├── Calls `WeatherService` (`backend/src/services/weather.py`)
      ▼
External Weather API (Open-Meteo REST API)
      ├── 1. Geocoding: `https://geocoding-api.open-meteo.com/v1/search?name=Veraval`
      └── 2. Forecast: `https://api.open-meteo.com/v1/forecast?latitude=20.9077&longitude=70.3678`
      │
      ▼
Structured JSON Response (`success: true`, temp, condition, precipitation, date)
      │
      ▼
LLM Speech Synthesis (Google Gemini)
      │ Converts structured data to natural speech in target script (Devanagari/Gujarati)
      ▼
Text-to-Speech (Murf Falcon TTS)
      │ Audio Stream
      ▼
User Spoken Output ("Veravalમાં આજે તાપમાન 28 ડિગ્રી સેલ્સિયસ છે...")
```

---

## 2. Tool Schema & Specification

### Tool Name
`get_weather`

### Tool Description
```
Retrieve live current or forecast weather data for a requested location in India or globally.
Use this tool ALWAYS whenever the user asks about current, today's, tomorrow's, or upcoming weather,
temperature, rain, precipitation, wind, or weather forecast for any location.
Do NOT use general LLM knowledge for current weather.
```

### Parameters
| Name | Type | Description | Required | Default |
|------|------|-------------|----------|---------|
| `location` | `string` | City or district name (e.g., "Veraval", "Ahmedabad", "Mumbai") | Yes* | `""` (Inferred from Day 4 memory) |
| `forecast_days` | `integer` | Number of forecast days (1 to 7) | No | `1` |

---

## 3. Success Response Payload
```json
{
  "success": true,
  "data": {
    "location": "Veraval",
    "region": "Gujarat",
    "country": "India",
    "temperature_c": 28,
    "feels_like_c": 32,
    "condition": "Overcast",
    "humidity_percent": 83,
    "precipitation_probability": 97,
    "wind_kmh": 24,
    "forecast_date": "2026-08-10",
    "source": "Open-Meteo",
    "retrieved_at": "2026-08-10T11:30:00Z"
  }
}
```

---

## 4. Failure Response Payload
```json
{
  "success": false,
  "error": "weather_service_unavailable",
  "message": "Failed to retrieve live weather data from Open-Meteo API."
}
```

### Error Codes
- `missing_location`: Location not supplied and not found in saved user profile.
- `invalid_location`: Provided location string was blank or malformed.
- `location_not_found`: Open-Meteo geocoding could not find coordinates for location.
- `weather_service_timeout`: Network request exceeded 5.0 second timeout limit.
- `weather_service_unavailable`: HTTP error or external API error.

---

## 5. Timeout & Security Bounding
- Bounded by **5.0-second timeout** (`httpx.TimeoutException`).
- Automatic retry or graceful degradation to spoken failure message.
- No exposure of stack traces or API internals to end user.

---

## 6. Testing Verification

Run weather unit & integration test suite:
```bash
cd backend
uv run pytest tests/test_weather_tool.py
```
