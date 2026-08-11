# Day 6 — Outbound Calls: Bharat Voice AI

## Summary
In Day 6, Bharat Voice AI evolves from a passive inbound-only voice agent to a proactive outbound AI voice assistant capable of initiating phone calls to registered users when critical weather alerts (such as high rain probability or severe thunderstorms) occur in their saved location.

## Architecture Flow

```
Weather Alert / Trigger
        │
        ▼
Open-Meteo Weather API (`get_weather`)
        │
        ▼
Weather Alert Decision Service (`should_call_user`)
   ├── 1. Consent Check (`outbound_call_consent == True`, `opted_out == False`)
   ├── 2. E.164 Phone Validation (+91...)
   ├── 3. Calling Hours Check (08:00 - 20:00)
   └── 4. Duplicate Suppression (<24h check)
        │
        ▼
Outbound Call Manager (`place_outbound_call`)
        │
        ├── Generates opaque room name (`bharat-outbound-{user_hash}-{timestamp}`)
        ├── Dispatches Agent (`LiveKitAPI.agent_dispatch.create_dispatch`)
        └── Dials SIP Participant (`LiveKitAPI.sip.create_sip_participant`)
        │
        ▼
Twilio / LiveKit SIP Telephony Trunk
        │
        ▼
Phone Rings → Callee Answers
        │
        ▼
Bharat Voice AI Agent Connects (Murf Falcon + Deepgram + Gemini)
   ├── 1. Spoken Mandatory Opening:
   │      - WHO: "Bharat Voice AI"
   │      - WHY: Weather alert for saved location (Veraval)
   │      - STOP: How to opt out ("tell me if you don't want future calls")
   ├── 2. Multilingual Response (English / Hindi / Gujarati native script)
   ├── 3. Opt-out Tool (`update_outbound_consent`)
   └── 4. Hangup Tool (`end_call`)
```

## Key Capabilities & Security
- **Explicit Consent**: Outbound calls are ONLY placed if `outbound_call_consent = True` and `opted_out = False`.
- **Mandatory 3-Part Spoken Opening**: The agent immediately identifies itself, states the reason for calling, and explains how to stop future calls.
- **Log Privacy**: Phone numbers are masked in normal application logs (`+91******3210`).
- **Test Mode Protection**: `OUTBOUND_TEST_MODE=true` redirects all development calls exclusively to `OUTBOUND_TEST_PHONE_NUMBER`.
- **Database Persistence**: SQLite tracks user profiles and records all call lifecycles in the `outbound_calls` table.

## Quickstart Testing
```bash
# Run test suite
cd backend
uv run pytest tests/test_outbound_calls.py

# Place a test outbound call
uv run python scripts/test_outbound_call.py --user-id gautam --phone +919876543210
```
