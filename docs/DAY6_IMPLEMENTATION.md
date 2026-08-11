# Bharat Voice AI — Day 6 Implementation Blueprint: Outbound Calling

## 1. Existing Architecture
Bharat Voice AI is a real-time multilingual voice AI agent built with:
- **LiveKit Agents SDK (~1.4)** for RTC audio transport, event handling, and agent dispatch.
- **Deepgram Nova-3** for speech-to-text with multilingual auto-detection.
- **Google Gemini (gemini-2.0-flash)** for LLM logic and tool orchestration.
- **Murf Falcon TTS (livekit-murf)** for ultra-low-latency voice synthesis with Indian accents (Pooja, Samar, Anisha).
- **SQLite Database (`data/bharat_voice.db`)** for persistent caller profiles and memory.
- **Open-Meteo REST API** for real-time weather & rain forecast queries.
- **Next.js + Tailwind CSS** frontend UI supporting live audio visualizers and status state machines.

## 2. Existing Day 4 Memory System
- Database schema (`users` table): `user_id`, `name`, `language_preference`, `facts` (JSON string), `created_at`, `updated_at`, `last_interaction`.
- `MemoryService` singleton in `backend/src/memory/memory_service.py` with automatic credential scrubbing for passwords, OTPs, PINs, bank info, card numbers, and medical notes.
- Function tools: `@function_tool` decorator on `Assistant` / `BharatVoiceAgent` for `remember_fact`, `get_caller_profile`, `forget_user_memory`.

## 3. Existing Day 5 Weather Tool
- `WeatherService` in `backend/src/services/weather.py` querying Open-Meteo geocoding & forecast endpoints.
- Returns current temperature, condition (WMO weather codes), humidity, wind speed, and daily `precipitation_probability`.
- Agent function tool `get_weather` in `backend/src/memory/tools.py` enables conversational weather checks with fallback to user's saved location.

## 4. New Outbound-Call Architecture
- **Trigger Engine (`weather_alert_service.py`)**: Checks weather forecasts against user profile locations and consent status.
- **Telephony Service (`telephony/outbound.py` & `telephony/call_manager.py`)**:
  1. Validates caller phone number in E.164 format.
  2. Verifies `outbound_call_consent == True`, `opted_out == False`, and current time within `OUTBOUND_CALL_START_HOUR` and `OUTBOUND_CALL_END_HOUR`.
  3. Checks duplicate call logs in `outbound_calls` table.
  4. Generates unique room name: `bharat-outbound-{user_id_hash}-{timestamp}`.
  5. Dispatches `bharat-voice-ai` agent using LiveKit `LiveKitAPI.agent_dispatch.create_dispatch()`.
  6. Initiates SIP call using LiveKit `LiveKitAPI.sip.create_sip_participant(CreateSIPParticipantRequest(...))`.
- **Outbound Agent Session (`agent.py` & `agent/voice_agent.py`)**:
  1. Detects outbound call type from room metadata.
  2. Waits for participant connection without auto-speaking inbound greeting.
  3. Speaks mandatory opening: WHO is calling, WHY (weather alert), and HOW to opt out.
  4. Executes conversation, listens for opt-out requests, and invokes hangup tool upon completion.

## 5. SIP Provider Integration
- Uses **Twilio SIP Trunking** or compatible LiveKit Telephony SIP Trunk provider.
- Configuration variables in `.env.local`:
  - `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
  - `SIP_TRUNK_ID`, `SIP_TRUNK_HOSTNAME`, `SIP_AUTH_USERNAME`, `SIP_AUTH_PASSWORD`
  - `OUTBOUND_PHONE_NUMBER`, `OUTBOUND_TEST_PHONE_NUMBER`, `OUTBOUND_TEST_MODE=true`

## 6. Call Trigger & Alert Decision Rules
- Trigger condition: `precipitation_probability >= WEATHER_ALERT_RAIN_THRESHOLD` (default 70%) OR severe weather WMO code (thunderstorms, heavy rain 65, 82, 95-99).
- Configurable environment variable: `WEATHER_ALERT_RAIN_THRESHOLD=70`.
- Calling hours guardrail: `OUTBOUND_CALL_START_HOUR` (default 8) to `OUTBOUND_CALL_END_HOUR` (default 20).
- Duplicate prevention: Check if an alert call for the same reason was delivered to the user within the last 24 hours.

## 7. Call Flow
1. **Alert Evaluation**: `WeatherAlertService` identifies user matching criteria.
2. **Pre-call Validation**: Verify E.164 phone, `outbound_call_consent == True`, non-opted-out, within hours, no recent duplicate.
3. **Room & Dispatch**: Create LiveKit room + dispatch agent with call metadata (`user_id`, `reason`, `language`).
4. **SIP Dialing**: Issue `create_sip_participant`.
5. **Answer & Greeting**: User answers; agent delivers mandatory 3-part opening in user's preferred language (English/Hindi/Gujarati in native script).
6. **Interaction**: Answer questions, handle language switching or consent updates.
7. **Call Termination**: Clean hangup via `end_call` tool or participant disconnect event, and update call status in database.

## 8. Call Outcomes & Retry Policy
- **Tracked Statuses**: `QUEUED`, `DIALING`, `ANSWERED`, `COMPLETED`, `NO_ANSWER`, `BUSY`, `REJECTED`, `VOICEMAIL`, `FAILED`, `OPTED_OUT`.
- **Retry Policy**:
  - `NO_ANSWER` / `BUSY`: Maximum 1 conservative retry after delay.
  - `REJECTED` / `OPTED_OUT`: NEVER retry.
  - `VOICEMAIL`: Speak short alert message and end call without retry.

## 9. Opt-Out Behavior
- If user requests to stop calls ("Stop calling me", "Don't call me again", "મને ફરી ફોન ન કરશો", "मुझे दोबारा फोन मत करना"):
  1. Agent confirms request in user's language.
  2. Sets `outbound_call_consent = False` and `opted_out = True` in SQLite database.
  3. Gracefully ends call via `end_call` tool.
  4. Subsequent alert evaluations immediately block calls for this user.

## 10. Testing Plan
1. **Automated Unit & Integration Tests (`tests/test_outbound_calls.py`)**:
   - Test consent checks, phone number E.164 validation, calling hours verification, duplicate prevention, retry policy logic, database schema migrations, and call logging.
   - Use mocked LiveKit API clients.
2. **Development Test Script (`scripts/test_outbound_call.py`)**:
   - Controlled invocation requiring `OUTBOUND_TEST_MODE=true` targeting `OUTBOUND_TEST_PHONE_NUMBER`.
3. **Live End-to-End Phone Call Verification**:
   - Place test call to test profile (Gautam, Gujarati, Veraval). Verify spoken opening, weather alert delivery, opt-out processing, database state update, and clean call termination.
