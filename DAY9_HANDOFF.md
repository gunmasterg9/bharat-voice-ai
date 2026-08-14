# Day 9 - Specialist Agent Handoff

## Main Agent

**Bharat Voice AI** — The primary multilingual Indian voice assistant handling general queries, greetings, caller memory, human escalations, and intent routing.

## Specialist Agent

**Bharat Weather Specialist** — Dedicated weather specialist agent focusing exclusively on detailed weather queries, forecast calculations, location normalization, and weather follow-ups using real Open-Meteo weather data.

## Handoff Trigger

Handoff occurs automatically via the `@function_tool async def handoff_to_weather_specialist(...)` tool whenever the user asks for:
- Current or today's weather
- Temperature or feels-like temperature
- Rain, rainfall, precipitation, humidity, or wind speed
- Today's high/low forecast or weather-related follow-ups

## Example

**User:**
"What is the weather today in Veraval?"

**Main Agent:**
"For detailed weather information, I'll connect you with our weather specialist."

**Specialist:**
"Namaste, I'm the Bharat Weather Specialist. I'll help you with the weather information you requested."

**Specialist:**
"The latest weather in Veraval is 27°C with overcast conditions and 85% humidity."

## Context

Conversation context, caller identity (`user_id`), saved user facts, and active language preference are preserved across handoff:
- **Language & Native Script Preservation**: Active conversation language is inherited and mapped into native scripts (Devanagari script for Hindi, Gujarati script for Gujarati, Latin script for English/Hinglish).
- **Original Request Inheritance**: The original query (`"What is the weather today in Veraval?"`) is passed directly in the specialist context, allowing immediate tool execution without requiring the caller to repeat themselves.

## Tool

- **`get_weather`**: An executable LiveKit `@function_tool` that accepts `location: str` and `forecast_days: int = 1`.
- Calls the real Open-Meteo REST API (`services/weather.py`) and returns live temperature, condition, precipitation probability, humidity, and wind speed.
- The raw JSON tool return remains strictly internal to the pipeline context and is converted by the LLM into spoken natural language without exposing raw tool parameters or JSON objects.

## Failure Handling

- **Handoff Failure**: If specialist instantiation or session updating fails, the Main Agent logs the error and politely responds: *"I'm unable to connect you to the weather specialist right now, but I'll continue helping you here."*
- **Weather API Failure**: If `get_weather` fails or Open-Meteo is unreachable, the Specialist states: *"Sorry, I couldn't retrieve the latest weather information right now."* and never hallucinates weather values.

## Testing

The Day 9 multi-agent architecture and handoff flow are validated by:
1. `tests/test_day9_specialist_handoff.py`: 15 comprehensive unit & integration tests covering main agent routing, native LiveKit handoff, language preservation across native scripts, code-mixed Hinglish/Gujlish queries, weather follow-up context retention, and failure handling.
2. `tests/test_weather_tool.py`: Tests for real Open-Meteo weather API integration, location normalization (e.g., "Vedawal" -> "Veraval"), and fallback handling.
3. **Regression Suite**: Full test suite (`124 passed`) verifying no regressions in Days 1-8 functionality.
