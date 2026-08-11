# Bharat Voice AI — Multilingual Voice Assistant for India 🇮🇳

[![Voice for Bharat Challenge 2026](https://img.shields.io/badge/Voice%20for%20Bharat-Challenge%202026-orange.svg)](https://github.com/murf-ai/voice-for-bharat-challenge-2026)
[![TTS](https://img.shields.io/badge/TTS-Murf%20Falcon%20(~100ms)-blue.svg)](https://murf.ai/falcon)
[![Framework](https://img.shields.io/badge/Framework-LiveKit%20Agents%201.4-green.svg)](https://docs.livekit.io/)
[![Tests](https://img.shields.io/badge/Tests-46%20Passed-brightgreen.svg)]()

**Bharat Voice AI** is a production-ready, multilingual voice assistant built for India as part of the official **10 Days of Voice Agents — #VoiceForBharat Edition** challenge hosted by [Murf AI](https://murf.ai/).

- **Track Selected:** 🌾 **Farm & Field** (*Kisan Mitra — Voice Advisory for Indian Farmers*)
- **Core Problem Solved:** Provides Indian farmers with hands-free, spoken access to crop advisory, mandi market rates (with source/date transparency), pest alerts, and weather guidance in their preferred native language (Hindi, Gujarati, Indian English, Hinglish, Gujlish).

---

## 🛠️ Technology Stack

- **Text-to-Speech (TTS):** [Murf Falcon](https://murf.ai/falcon) & Falcon 2 (~100 ms streaming latency, Indian English, Hindi, Gujarati voices).
- **Speech-to-Text (STT):** Deepgram Nova-3 (`model="nova-3"`, multilingual streaming).
- **LLM Engine:** Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`).
- **Agent Orchestrator:** LiveKit Agents SDK (`livekit-agents ~1.4`), Python `AgentServer` & `AgentSession`.
- **Turn & Voice Activity Detection:** Silero VAD & LiveKit Turn Detector (`MultilingualModel`).
- **Database / Memory:** Embedded SQLite (`backend/data/bharat_voice.db`) with WAL mode, parameterized queries, and explicit consent management.
- **External Tools:** Open-Meteo REST API (Geocoding & Forecast API for live weather lookups).
- **Frontend UI:** Next.js (React, TypeScript, Tailwind CSS, LiveKit Agents UI).

---

## 📋 Day-by-Day Implementation Summary (Day 1 → Day 5)

### 🎙️ Day 1: Get Your Voice Agent Talking
- **Starter Foundation:** Configured `murf-livekit-starter` with Python 3.10+, `uv` package manager, and Next.js.
- **Track Selection:** Locked in **Farm & Field** track to support agricultural advisory.
- **Indian Voice Configuration:** Configured Murf Falcon TTS for Indian English, Hindi, and Gujarati speech streaming.
- **WebRTC Voice Pipeline:** Integrated STT (Deepgram Nova-3) → LLM (Gemini) → TTS (Murf Falcon) streaming audio pipeline over WebRTC.

### 🛡️ Day 2: Personality, Job, and Limits
- **Call Objectives Defined:**
  1. Assist farmers with crop health, pest prevention, and fertilizer application steps.
  2. Deliver accurate mandi (market) crop prices with explicit source and date attribution.
  3. Provide localized weather alerts and crop management guidance.
- **Structured System Prompt:** Implemented prompt sections in [`backend/src/agent/prompts.py`](file:///d:/Desktop/Challenge/10%20Days%20of%20AI%20Voice%20Agents/murf-livekit-starter/backend/src/agent/prompts.py):
  - `IDENTITY`: Female persona ("Bharat Voice AI"), female grammar agreement rules in Hindi ("कर सकती हूँ").
  - `OBJECTIVES`: 2–3 clear outcomes per call.
  - `KNOWLEDGE`: Agricultural domain scope; refusal of medical diagnosis, legal advice, or financial guarantees.
  - `LANGUAGE`: Auto-detects and mirrors user's register (Hindi, Gujarati, English, Hinglish, Gujlish).
  - `GUARDRAILS`: Never state prices as facts without date/source, never claim government scheme approval, standard escalation script.
  - `STYLE`: Speech-first 10–20 word sentences, natural pauses, spoken numbers as words.
- **Guardrail Escalation Script:**
  > *"I'm sorry, I can't safely help with that. Please contact the appropriate professional or official service. Is there something else I can help you with today?"*
- **Silence Handling Protocol:**
  - Turn 1 Silence: *"Are you still there?"*
  - Turn 2 Silence: *"No problem. Feel free to come back anytime. Goodbye."*

### 🎨 Day 3: Personalise Your Agent's Frontend
- **Tailored Agricultural UI:** Built Next.js interface ([`app.tsx`](file:///d:/Desktop/Challenge/10%20Days%20of%20AI%20Voice%20Agents/murf-livekit-starter/frontend/components/app/app.tsx)) styled specifically for farmers.
- **5 Explicit Agent States:**
  1. **`Ready`**: Initial state with one clear "Start Conversation" CTA button.
  2. **`Connecting`**: Joining the LiveKit WebRTC session with visual spinner.
  3. **`Listening`**: VAD active, indicating agent is listening to the user.
  4. **`Speaking`**: Agent is replying via Murf Falcon audio stream.
  5. **`Call Ended`**: Session ended, displaying summary and reconnect option.
- **Dual Visualizer:** Real-time visual audio waves and status badges ([`VoiceAgent.tsx`](file:///d:/Desktop/Challenge/10%20Days%20of%20AI%20Voice%20Agents/murf-livekit-starter/frontend/components/VoiceAgent.tsx)) showing speaker activity.
- **Microphone Permission Handling:** Created [`PermissionError.tsx`](file:///d:/Desktop/Challenge/10%20Days%20of%20AI%20Voice%20Agents/murf-livekit-starter/frontend/components/PermissionError.tsx) displaying clear instructions if browser mic access is blocked.
- **Live Transcript & Logs:** Built live transcript viewer and real-time backend log modal.

### 💾 Day 4: Give Your Agent a Memory That Lasts
- **Embedded SQLite Database:** Disk-backed storage at `backend/data/bharat_voice.db` with WAL mode and auto-schema migration.
- **Farm & Field Facts Schema:**
  ```sql
  CREATE TABLE IF NOT EXISTS users (
      user_id TEXT PRIMARY KEY,
      name TEXT,
      language_preference TEXT,
      facts TEXT DEFAULT '{}', -- JSON string containing district, land size, crops grown
      last_interaction TEXT, -- Timezone-aware ISO 8601 timestamp
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
  );
  ```
- **Persistent User ID Routing:** Browser `localStorage` persists caller ID (`bharat_voice_user_id`) → Token endpoint `/api/token?userId=...` → `participantIdentity` in LiveKit JWT → Resolved in `agent.py`.
- **Dynamic Memory Tools:**
  - `lookup_caller`: Retrieves returning caller profile on call start.
  - `save_caller_memory`: Persists name, language, and crop facts **ONLY IF `user_consent=True`**.
  - `forget_caller`: Completely deletes SQLite profile row **ONLY IF `user_confirmation=True`**.
- **Explicit Consent Protocol ("Ask before you save"):**
  - Verbal consent required before storing names or facts (*"Would you like me to remember your name and crops for next time?"*).
  - Explicit refusal (*"No"*, *"Don't save"*) sets state to `DENIED` (*"Of course. I won't save that information."*).
- **Sensitive Credential Scrubbing:** Automatically blocks passwords, PINs, OTPs, Aadhaar/PAN IDs, bank accounts, and written medical notes.
- **Returning Caller Experience:** Greets returning farmers by name and resumes context:
  > *"Namaste Ramesh! Last time we spoke about your cotton crop in Ahmedabad. Did the pest spraying help?"*

### 🛠️ Day 5: Real-Time External Tools (Weather Lookup)
- **Live Data Integration:** Teaches Bharat Voice AI to use a real external tool (`get_weather`) powered by **Open-Meteo REST API** for live weather queries instead of static LLM training data.
- **Automatic Tool Invocation:** The agent automatically detects live weather queries (*"What's the weather in Veraval today?"*, *"Will it rain tomorrow in Ahmedabad?"*, *"વેરાવળમાં આજે હવામાન કેવું છે?"*) and invokes `get_weather`.
- **Location Resolution & Memory Synergy:**
  - Supports Indian cities and districts (e.g., Veraval, Gir Somnath, Ahmedabad, Rajkot, Mumbai, Delhi).
  - If no location is specified in the query (*"What's the weather today?"*), the tool automatically checks the caller's Day 4 saved SQLite profile for a stored location before asking the user to clarify.
- **Structured Data & Failure Handling:**
  - Returns structured JSON payloads (`success: true/false`, temperature, feels like, condition, precipitation probability, wind speed).
  - Bounded by a **5.0-second network timeout**.
  - On API failure or DNS error, the agent speaks a graceful fallback message (*"Sorry, I couldn't retrieve the latest weather information right now."*) and **never** hallucinates weather numbers.
### 📞 Day 6: Make Outbound Calls (Proactive Weather & Rain Alerts)
- **Outbound Telephony Architecture:** Uses LiveKit Telephony API (`CreateSIPParticipantRequest` & `CreateAgentDispatchRequest`) integrated with Twilio SIP Trunking.
- **Proactive Rain Alert Use Case:** Checks Open-Meteo forecasts for registered users with saved locations (e.g. Gautam in Veraval). Initiates an outbound call when `precipitation_probability >= WEATHER_ALERT_RAIN_THRESHOLD` (configurable default 70%).
- **Mandatory 3-Part Spoken Opening:** In the first 2 spoken sentences, the agent explicitly states:
  1. **WHO**: *"Hello Gautam, this is Bharat Voice AI calling..."*
  2. **WHY**: *"...with a weather alert for your saved location Veraval."*
  3. **STOP/OPT-OUT**: *"...If you don't want these alert calls in the future, just tell me and I'll stop them."*
- **Explicit Consent & Opt-Out Persistence:** Stores `outbound_call_consent` and `opted_out` flags in SQLite database (`data/bharat_voice.db`). If the user says *"Stop calling me"* or *"મને ફરી ફોન ન કરશો"*, the agent invokes `update_outbound_consent(opt_out=True)`, confirms politely, and ends the call cleanly via `end_call()`.
- **Calling Hours & Duplicate Suppression:** Enforces reasonable calling hours (`OUTBOUND_CALL_START_HOUR=8` to `OUTBOUND_CALL_END_HOUR=20`) and suppresses duplicate alert calls within 24 hours.
- **Log Privacy & Test Mode:** Masks phone numbers in normal logs (`+91******3210`) and enforces `OUTBOUND_TEST_MODE=true` targeting `OUTBOUND_TEST_PHONE_NUMBER` for safety.

---

## 📂 Repository Structure

```
murf-livekit-starter/
├── DAY5_IMPLEMENTATION.md    # Day 5 Technical Architecture Document
├── DAY4_IMPLEMENTATION.md    # Day 4 Technical Architecture Document
├── MEMORY_RED_TEAM.md        # Privacy & Security Red Team Suite
├── docs/
│   ├── DAY5.md              # Day 5 Weather Tool Architecture & Schemas
│   ├── DAY4.md              # Day 4 Memory Specification
│   └── DAY3.md              # Day 3 Frontend Specification
├── README.md                 # Master README (This File)
├── backend/
│   ├── data/
│   │   └── bharat_voice.db   # Persistent SQLite Database
│   ├── src/
│   │   ├── agent.py          # Entrypoint & Participant ID Resolver
│   │   ├── agent/            # Prompts, Voice Agent, Guardrails, Memory Tools
│   │   ├── memory/           # Database Manager & Memory Service
│   │   └── services/         # Gemini LLM, Deepgram STT, Murf Falcon TTS, Weather Service
│   └── tests/                # Pytest Suite (41/41 Tests Passed)
└── frontend/                 # Next.js Voice UI
    ├── app/api/token/route.ts# Token Route with Persistent UserId
    └── components/           # Voice Agent UI & State Management
```

---

## 🚀 Getting Started

### 1. Environment Setup

Copy `backend/.env.example` to `backend/.env.local` and configure required API keys:
```env
LIVEKIT_URL=wss://your-livekit-url
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
MURF_API_KEY=your_murf_key
DEEPGRAM_API_KEY=your_deepgram_key
GOOGLE_API_KEY=your_google_gemini_key
```

Copy `frontend/.env.example` to `frontend/.env.local` and set:
```env
LIVEKIT_URL=wss://your-livekit-url
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
```

### 2. Run Backend Agent Server

```bash
cd backend
uv sync
uv run python src/agent.py dev
```

### 3. Run Frontend UI

```bash
cd frontend
pnpm install
pnpm dev
```

Open `http://localhost:3000` in your browser.

---

## 🗣️ Example Day 5 Live Tool Demo Session

### Scenario 1: Real-Time Weather Lookup (Veraval):
- **Farmer**: *"What's the weather in Veraval today?"*
- **Agent Logs**:
  - `[TOOL] get_weather called`
  - `[TOOL] location = Veraval`
  - `[TOOL] weather request started for location 'Veraval'`
  - `[TOOL] weather request successful for 'Veraval'`
- **Spoken Response**: *"According to the latest weather data, the current temperature in Veraval is around 28 degrees Celsius with overcast skies and high probability of rain today."*

### Scenario 2: Gujarati Multilingual Weather Query:
- **Farmer**: *"વેરાવળમાં આજે હવામાન કેવું છે?"*
- **Spoken Response**: *"તાજેતરના હવામાન ડેટા મુજબ, આજે વેરાવળમાં વરસાદની 97 ટકા શક્યતા સાથે તાપમાન લગભગ 28 ડિગ્રી સેલ્સિયસ છે."*

### Scenario 3: Memory Location Fallback:
- **Farmer**: *"What's the weather today?"*
- **Agent**: *(Detects stored user profile with location `Veraval`)* -> *"For your saved location Veraval, today's temperature is around 28 degrees Celsius with overcast skies."*

### Scenario 4: Weather API Failure Handling (Simulated Timeout):
- **Farmer**: *"What's the weather in Ahmedabad?"* -> *(Simulated API failure/timeout)*
- **Spoken Response**: *"Sorry, I couldn't retrieve the latest weather information right now. Please try again in a moment."*

---

## 📜 License & Acknowledgments

Built for the **Voice for Bharat Challenge 2026** powered by [Murf AI](https://murf.ai/).
