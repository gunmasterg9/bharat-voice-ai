# Day 5 Implementation Blueprint — Real-Time External Tools (Weather Lookup)

## 1. Existing Architecture Overview

Bharat Voice AI is a real-time multilingual voice assistant powered by:
- **Speech-to-Text (STT)**: Deepgram Nova-3 for low-latency multi-dialect speech transcription.
- **Large Language Model (LLM)**: Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`) via `google-genai` and LiveKit Agents framework.
- **Text-to-Speech (TTS)**: Murf Falcon (`livekit-murf`) streaming TTS for ultra-fast, human-like voice synthesis.
- **Voice Activity Detection & Turn Detection**: Silero VAD + LiveKit Multilingual Turn Detector.
- **Transport / Orchestration**: LiveKit WebRTC server and LiveKit Agents SDK v1.4.

---

## 2. Existing Day 4 Memory Architecture

In Day 4, persistent memory was integrated to allow returning callers to be recognized across sessions:
- **Storage Layer**: SQLite database located at `backend/data/memory.db`.
- **Memory Service (`backend/src/memory/memory_service.py`)**:
  - Manages `users` and `caller_facts` tables.
  - Implements privacy boundaries (`SENSITIVE_KEYWORDS` blocking passwords, OTPs, PINs, bank details).
  - Handles explicit user consent requirement (`user_consent=True`) before saving profile information.
  - Supports Forget-Me protocol (`delete_user`).
- **Agent Tools (`backend/src/agent/voice_agent.py`)**:
  - `lookup_caller`: Retrieves stored caller profile on connection.
  - `save_caller_memory`: Persists user preferences and non-sensitive facts after explicit consent.
  - `forget_caller`: Completely deletes caller profile upon user confirmation.

---

## 3. New Day 5 Tool Architecture

Day 5 introduces **external tool execution** capability so that Bharat Voice AI can provide live/current data without relying on static LLM training data.

### Architectural Flow:
```
User (Voice)
  │
  ▼
Deepgram STT (Audio → Text)
  │
  ▼
Gemini LLM (Evaluates prompt & detects live weather intent)
  │
  ├── Calls @function_tool `get_weather(location="Veraval")`
  │
  ▼
BharatVoiceAgent (`backend/src/agent/voice_agent.py`)
  │
  ├── Checks Day 4 Memory if location is missing ("What's the weather today?")
  ├── Invokes `WeatherService` (`backend/src/services/weather.py`)
  │
  ▼
Open-Meteo REST API
  ├── Geocoding API (`https://geocoding-api.open-meteo.com/v1/search`)
  └── Forecast API (`https://api.open-meteo.com/v1/forecast`)
  │
  ▼
Structured Response (`success: true`, location, temp, condition, precipitation %, date)
  │
  ▼
Gemini LLM (Formats structured result into natural multilingual speech: Devanagari/Gujarati)
  │
  ▼
Murf Falcon TTS (Streams voice back to user WebRTC session)
```

---

## 4. Weather API Selection: Open-Meteo

**Selected Provider**: [Open-Meteo](https://open-meteo.com/)

**Key Advantages**:
1. **Free & Public**: No API key requirement for standard non-commercial usage.
2. **High Precision for India**: Built-in Geocoding API resolves Indian towns and districts (e.g. Veraval, Gir Somnath, Ahmedabad, Rajkot, Surat, Vadodara, Mumbai, Delhi, Bengaluru, etc.).
3. **Comprehensive Parameters**: Provides temperature, apparent temperature (feels like), humidity, WMO weather codes, wind speed, daily high/low, and max precipitation probability.

---

## 5. Tool Input & Output Contracts

### Tool Name: `get_weather`

### Input Schema:
```python
location: str  # Required or auto-inferred from saved user profile (e.g., "Veraval")
forecast_days: int  # Optional forecast range (default: 1 for current/today)
```

### Output Contract (Success):
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

### Output Contract (Failure):
```json
{
  "success": false,
  "error": "weather_service_unavailable",
  "message": "Failed to retrieve live weather data from Open-Meteo API."
}
```

---

## 6. Failure Handling & Security

1. **Timeout**: HTTP requests are bounded to a **5.0-second timeout** using `httpx.AsyncClient`.
2. **DNS / Connection Errors**: Caught by `httpx.RequestError` and wrapped in `success: false`.
3. **Location Not Found**: If Geocoding API returns empty results, returns `success: false` with `error: "location_not_found"`.
4. **No Hallucination Policy**: If the tool fails, the agent is instructed by `SYSTEM_PROMPT` to state:
   > "Sorry, I couldn't retrieve the latest weather information right now. Please try again in a moment."
   The LLM **never** fabricates temperatures or rain probabilities.
5. **Input Sanitization**: User-provided location strings are stripped and checked against invalid characters before API calls.

---

## 7. Data Freshness & Probabilistic Speech

- Responses explicitly identify current/latest data timestamp or date when relevant.
- Forecast responses use probabilistic phrasing:
  - English: *"Today's forecast for Veraval shows a 97 percent chance of rain with temperatures around 28 degrees Celsius."*
  - Hindi: *"नवीनतम मौसम डेटा के अनुसार, आज वेरावल में बारिश की 97 प्रतिशत संभावना है और तापमान लगभग 28 डिग्री सेल्सियस है।"*
  - Gujarati: *"તાજેતરના હવામાન ડેટા મુજબ, આજે વેરાવળમાં વરસાદની 97 ટકા શક્યતા છે અને તાપમાન લગભગ 28 ડિગ્રી સેલ્સિયસ છે."*

---

## 8. Testing Plan

1. **Service Unit Tests (`backend/tests/test_weather_tool.py`)**:
   - Verify Geocoding resolution for Indian locations (Veraval, Gir Somnath, Ahmedabad, Mumbai).
   - Mock network failures, HTTP 500 errors, timeouts, and malformed JSON responses.
   - Verify memory location fallback when input location is blank.
2. **LLM Tool Call Integration Tests**:
   - Verify Gemini automatically triggers `get_weather` for current weather queries.
   - Test multilingual execution (English, Hindi, Gujarati).
   - Verify spoken failure message on simulated API failure.
3. **Regression Tests**:
   - Run complete suite (`uv run pytest`) covering Day 1-4 tests (33+ assertions).
