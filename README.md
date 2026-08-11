# Bharat Voice AI — Multilingual Voice Assistant for India 🇮🇳

[![Voice for Bharat Challenge 2026](https://img.shields.io/badge/Voice%20for%20Bharat-Challenge%202026-orange.svg)](https://github.com/murf-ai/voice-for-bharat-challenge-2026)
[![TTS](https://img.shields.io/badge/TTS-Murf%20Falcon%20(~100ms)-blue.svg)](https://murf.ai/falcon)
[![Framework](https://img.shields.io/badge/Framework-LiveKit%20Agents%201.4-green.svg)](https://docs.livekit.io/)
[![Tests](https://img.shields.io/badge/Tests-56%20Passed-brightgreen.svg)]()

**Bharat Voice AI is a multilingual voice agent that provides live weather updates, remembers user preferences, and proactively makes outbound calls for important weather alerts.**

- **Track Selected:** 🌦️ **Weather & Disaster Response** (*Real-Time Weather Voice Assistant & Proactive Alert System*)
- **Core Problem Solved:** Provides citizens, farmers, and travelers across India with hands-free, spoken access to live weather forecasts, proactive rain & extreme weather phone alert calls, saved location memory, and multilingual voice guidance in native Indian languages (Hindi, Gujarati, Indian English, Hinglish, Gujlish).

---

## 🏛️ System Architecture

### Inbound Voice Architecture:
```
User
 ↓
LiveKit
 ↓
Deepgram STT
 ↓
Gemini
 ↓
Tools / Memory
 ↓
Murf Falcon
 ↓
LiveKit Audio
```

### Outbound Telephony Architecture:
```
Bharat Voice AI
 ↓
LiveKit SIP
 ↓
Linphone
 ↓
Phone
```

---

## 🛠️ Technology Stack

- **Text-to-Speech (TTS):** [Murf Falcon](https://murf.ai/falcon) & Falcon 2 (~100 ms streaming latency, Indian English `Anisha`, `Pooja`, `Samar` voices).
- **Speech-to-Text (STT):** Deepgram Nova-3 (`model="nova-3"`, multilingual streaming).
- **LLM Engine:** Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`).
- **Agent Orchestrator:** LiveKit Agents SDK (`livekit-agents ~1.4`), Python `AgentServer` & `AgentSession`.
- **Turn & Voice Activity Detection:** Silero VAD & LiveKit Turn Detector (`MultilingualModel`).
- **Database / Memory:** Embedded SQLite (`backend/data/bharat_voice.db`) with WAL mode, parameterized queries, and explicit consent management.
- **External Tools:** Open-Meteo REST API (Geocoding & Forecast API for live weather lookups).
- **Telephony & SIP Outbound:** LiveKit SIP Trunking (`livekit.api`) & Linphone / Mobile app integration.
- **Frontend UI:** Next.js (React, TypeScript, Tailwind CSS, LiveKit Agents UI).

---

## 📋 Day-by-Day Implementation Summary (Day 1 → Day 6)

### 🎙️ Day 1: Voice Agent (Get Your Voice Agent Talking)
- **Starter Foundation:** Configured `murf-livekit-starter` with Python 3.10+, `uv` package manager, and Next.js.
- **Track Selection:** Locked in **Weather & Disaster Response** track to support real-time weather voice advisory.
- **Indian Voice Configuration:** Configured Murf Falcon TTS for Indian English (`Anisha`), Hindi, and Gujarati speech streaming.
- **WebRTC Voice Pipeline:** Integrated STT (Deepgram Nova-3) → LLM (Gemini) → TTS (Murf Falcon) streaming audio pipeline over WebRTC.

### 🛡️ Day 2: Persona + Guardrails (Personality, Job, and Limits)
- **Call Objectives Defined:**
  1. Assist users with current weather conditions, temperature, rain probability, and multi-day forecasts.
  2. Provide clear warnings for severe weather events (thunderstorms, heavy rainfall, heatwaves).
  3. Support localized weather queries across Indian cities and districts.
- **Structured System Prompt:** Implemented prompt sections in `backend/src/agent/prompts.py`:
  - `IDENTITY`: Female persona ("Bharat Voice AI"), female grammar agreement rules in Hindi ("कर सकती हूँ").
  - `OBJECTIVES`: 2–3 clear outcomes per call.
  - `KNOWLEDGE`: Weather and disaster safety scope; refusal of medical diagnosis, legal advice, or financial guarantees.
  - `LANGUAGE`: Auto-detects and mirrors user's register (Hindi, Gujarati, English, Hinglish, Gujlish) using native scripts (`नमस्ते`, `નમસ્તે`, `Hello`).
  - `GUARDRAILS`: Never state weather predictions without real-time tool verification, refusal script for out-of-scope topics.
  - `STYLE`: Speech-first 10–20 word sentences, natural pauses, spoken numbers as words.
- **Guardrail Escalation Script:**
  > *"I'm sorry, I can't safely help with that. Please contact the appropriate professional or official service. Is there something else I can help you with today?"*
- **Silence Handling Protocol:**
  - Turn 1 Silence: *"Are you still there?"*
  - Turn 2 Silence: *"No problem. Feel free to come back anytime. Goodbye."*

### 🎨 Day 3: Personalized Frontend (Personalise Your Agent's Frontend)
- **Tailored Weather UI:** Built Next.js interface (`frontend/components/app/welcome-view.tsx`) styled specifically for weather advisory.
- **5 Explicit Agent States:**
  1. **`Ready`**: Initial state with one clear "Start Conversation" CTA button.
  2. **`Connecting`**: Joining the LiveKit WebRTC session with visual spinner.
  3. **`Listening`**: VAD active, indicating agent is listening to the user (*"Listening to you"*).
  4. **`Speaking`**: Agent is replying via Murf Falcon audio stream (*"Bharat Voice AI is speaking"*).
  5. **`Call Ended`**: Session ended, displaying *"Conversation ended"* and *"Start Again"*.
- **Dual Visualizer:** Real-time visual audio waves and status badges (`frontend/components/VoiceAgent.tsx`) showing speaker activity.
- **Microphone Permission Handling:** Created `frontend/components/PermissionError.tsx` displaying: *"Microphone access is blocked. Please allow microphone permission in your browser settings and try again."*
- **Live Transcript & Logs:** Built live transcript viewer and real-time backend log modal.

### 💾 Day 4: Persistent Memory (Give Your Agent a Memory That Lasts)
- **Embedded SQLite Database:** Disk-backed storage at `backend/data/bharat_voice.db` with WAL mode and auto-schema migration.
- **User Location & Preferences Schema:**
  ```sql
  CREATE TABLE IF NOT EXISTS users (
      user_id TEXT PRIMARY KEY,
      name TEXT,
      language_preference TEXT,
      facts TEXT DEFAULT '{}', -- JSON string containing saved location, city, district
      last_interaction TEXT, -- Timezone-aware ISO 8601 timestamp
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
  );
  ```
- **Persistent User ID Routing:** Browser `localStorage` persists caller ID (`bharat_voice_user_id`) → Token endpoint `/api/token?userId=...` → `participantIdentity` in LiveKit JWT → Resolved in `agent.py`.
- **Dynamic Memory Tools:**
  - `lookup_caller`: Retrieves returning caller profile on call start.
  - `save_caller_memory`: Persists name, language, and saved location facts **ONLY IF `user_consent=True`**.
  - `forget_caller`: Completely deletes SQLite profile row **ONLY IF `user_confirmation=True`**.
- **Explicit Consent Protocol ("Ask before you save"):**
  - Verbal consent required before storing names or location preferences (*"Would you like me to remember your saved location for weather alerts?"*).
  - Explicit refusal (*"No"*, *"Don't save"*) sets state to `DENIED` (*"Of course. I won't save that information."*).
- **Sensitive Credential Scrubbing:** Automatically blocks passwords, PINs, OTPs, Aadhaar/PAN IDs, bank accounts, and written medical notes.
- **Returning Caller Experience:** Greets returning callers by name and resumes location context:
  > *"Namaste Gautam! Last time we checked weather for your location Veraval. Would you like today's forecast?"*

### 🛠️ Day 5: Real-Time Weather Tool (Real-Time Tool / Weather Lookup)
- **Live Data Integration:** Teaches Bharat Voice AI to use a real external tool (`get_weather`) powered by **Open-Meteo REST API** for live weather queries instead of static LLM training data.
- **Automatic Tool Invocation:** The agent automatically detects live weather queries (*"What's the weather in Veraval today?"*, *"Will it rain tomorrow in Ahmedabad?"*, *"વેરાવળમાં આજે હવામાન કેવું છે?"*) and invokes `get_weather`.
- **Location Resolution & Memory Synergy:**
  - Supports Indian cities and districts (e.g., Veraval, Gir Somnath, Ahmedabad, Rajkot, Mumbai, Delhi).
  - If no location is specified in the query (*"What's the weather today?"*), the tool automatically checks the caller's Day 4 saved SQLite profile for a stored location before asking the user to clarify.
- **Structured Data & Failure Handling:**
  - Returns structured JSON payloads (`success: true/false`, temperature, feels like, condition, precipitation probability, wind speed).
  - Bounded by a **5.0-second network timeout**.
  - On API failure or DNS error, the agent speaks a graceful fallback message (*"Sorry, I couldn't retrieve the latest weather information right now."*) and **never** hallucinates weather numbers.

### 📞 Day 6: Outbound Voice Calls (Make Outbound Calls)
- **Outbound Telephony Architecture:** Uses LiveKit Telephony API (`CreateSIPParticipantRequest` & `CreateAgentDispatchRequest`) integrated with SIP Trunking for Linphone / mobile app calling.
- **Proactive Rain Alert Trigger:** Checks Open-Meteo forecasts for registered users with saved locations (e.g., Gautam in Veraval). Initiates an outbound call when `precipitation_probability >= WEATHER_ALERT_RAIN_THRESHOLD` (default 70%).
- **6-Step Interactive Outbound Call Lifecycle:**
  ```
  📞 1. Phone Rings -> Answer call on Linphone / Mobile App
        ↓
  👋 2. Intro & Weather Alert -> Agent speaks opening greeting & live weather info for Veraval
        ↓
  🗣️ 3. Follow-up Question -> Ask: "Will it rain tomorrow in Veraval?" -> Agent responds with forecast
        ↓
  🚫 4. Opt-Out Request -> Say: "Don't call me again" or "Stop calling me"
        ↓
  👋 5. Confirmation -> Agent confirms opt-out preference saved to SQLite DB
        ↓
  📴 6. Call Ends -> Agent automatically invokes end_call() and disconnects room
  ```
- **Mandatory 3-Part Spoken Opening:** In the first 2 spoken sentences, the agent explicitly states:
  1. **WHO**: *"Hello Gautam, this is Bharat Voice AI calling..."*
  2. **WHY**: *"...with a weather update for your saved location Veraval."*
  3. **STOP/OPT-OUT**: *"...If you don't want these alert calls in the future, just tell me and I'll stop them."*
- **Explicit Consent & Opt-Out Persistence:** Stores `outbound_call_consent` and `opted_out` flags in SQLite database (`data/bharat_voice.db`). If the user says *"Stop calling me"* or *"મને ફરી ફોન ન કરશો"*, the agent invokes `update_outbound_consent(opt_out=True)`, confirms politely, and ends the call cleanly via `end_call()`.
- **Calling Hours & Duplicate Suppression:** Enforces reasonable calling hours (`OUTBOUND_CALL_START_HOUR=8` to `OUTBOUND_CALL_END_HOUR=20`) and suppresses duplicate alert calls within 24 hours.
- **Log Privacy & Test Mode:** Masks phone numbers in normal logs (`+91******3210`) and enforces `OUTBOUND_TEST_MODE=true` targeting `OUTBOUND_TEST_PHONE_NUMBER` for safety.

---

## 📂 Repository Structure

```
murf-livekit-starter/
├── DAY6_OUTBOUND_RED_TEAM.md # Day 6 Outbound Call Red Team & Safety Audit
├── DAY5_IMPLEMENTATION.md    # Day 5 Technical Architecture Document
├── DAY4_IMPLEMENTATION.md    # Day 4 Technical Architecture Document
├── MEMORY_RED_TEAM.md        # Day 4 Privacy & Security Red Team Suite
├── docs/
│   ├── DAY1.md              # Day 1 Voice Agent Specification
│   ├── DAY2.md              # Day 2 Persona, Guardrails & Multilingual Specification
│   ├── DAY3.md              # Day 3 Frontend & Visualizer Specification
│   ├── DAY4.md              # Day 4 Persistent SQLite Memory Specification
│   ├── DAY5.md              # Day 5 Weather Tool Architecture & Schemas
│   ├── DAY6.md              # Day 6 Outbound Calling Specification & SIP Architecture
│   ├── DAY6_IMPLEMENTATION.md
│   └── DAY6_LINPHONE_SETUP.md# Linphone SIP Client Configuration Guide
├── README.md                 # Master README (This File)
├── backend/
│   ├── data/
│   │   └── bharat_voice.db   # Persistent SQLite Database
│   ├── src/
│   │   ├── agent.py          # Core Entrypoint & WebRTC Participant Resolver
│   │   ├── agent/            # Prompts, Voice Agent, Guardrails, Memory Tools
│   │   ├── memory/           # SQLite Database Manager & Memory Service
│   │   ├── services/         # Gemini LLM, Deepgram STT, Murf Falcon TTS, Weather & Alert Services
│   │   └── telephony/        # Outbound Calling, Call Manager & LiveKit SIP Integration
│   └── tests/                # Pytest Suite (56/56 Tests Passed)
│       ├── test_6step_outbound_flow.py # End-to-end 6-step lifecycle test suite
│       ├── test_outbound_calls.py      # Weather alert trigger & decision tests
│       └── test_outbound_linphone.py   # SIP dispatch & call manager integration tests
└── frontend/                 # Next.js Voice UI
    ├── app/api/token/route.ts# Token Route with Persistent UserId
    └── components/           # Voice Agent UI & State Management
```

---

## 🚀 Getting Started

### 1. Environment Setup

Copy `backend/.env.example` to `backend/.env.local` and configure required API keys:
```env
LIVEKIT_URL=wss://<YOUR_LIVEKIT_PROJECT_URL>
LIVEKIT_API_KEY=<YOUR_LIVEKIT_API_KEY>
LIVEKIT_API_SECRET=<YOUR_LIVEKIT_API_SECRET>
MURF_API_KEY=<YOUR_MURF_API_KEY>
DEEPGRAM_API_KEY=<YOUR_DEEPGRAM_API_KEY>
GOOGLE_API_KEY=<YOUR_GOOGLE_API_KEY>
LIVEKIT_SIP_OUTBOUND_TRUNK_ID=<YOUR_LIVEKIT_SIP_OUTBOUND_TRUNK_ID>
LINPHONE_USERNAME=<YOUR_LINPHONE_USERNAME>
LINPHONE_DOMAIN=sip.linphone.org
LINPHONE_SIP_URI=sip:<YOUR_LINPHONE_USERNAME>@sip.linphone.org
OUTBOUND_TEST_MODE=true
```

Copy `frontend/.env.example` to `frontend/.env.local` and set:
```env
LIVEKIT_URL=wss://<YOUR_LIVEKIT_PROJECT_URL>
LIVEKIT_API_KEY=<YOUR_LIVEKIT_API_KEY>
LIVEKIT_API_SECRET=<YOUR_LIVEKIT_API_SECRET>
```

### 2. Run Inbound Backend Agent Server

```bash
cd backend
uv sync
uv run python src/agent.py dev
```

### 3. Run Outbound Telephony Agent & Dial Script

In **Terminal 1** (Agent Worker):
```bash
cd backend
uv run python src/telephony/outbound/agent.py dev
```

In **Terminal 2** (Outbound Initiator):
```bash
cd backend
uv run python src/telephony/outbound/dial.py --to <YOUR_LINPHONE_USERNAME>
```

### 4. Run Frontend UI

```bash
cd backend
cd ../frontend
pnpm install
pnpm dev
```

Open `http://localhost:3000` in your browser.

---

## 🗣️ Example Live Voice Demo Sessions

### Scenario 1: Real-Time Weather Lookup (Veraval):
- **User**: *"What's the weather in Veraval today?"*
- **Agent Logs**:
  - `[TOOL] get_weather called`
  - `[TOOL] location = Veraval`
  - `[TOOL] weather request started for location 'Veraval'`
  - `[TOOL] weather request successful for 'Veraval'`
- **Spoken Response**: *"According to the latest weather data, the current temperature in Veraval is around 28 degrees Celsius with overcast skies and high probability of rain today."*

### Scenario 2: Gujarati Multilingual Weather Query:
- **User**: *"વેરાવળમાં આજે હવામાન કેવું છે?"*
- **Spoken Response**: *"તાજેતરના હવામાન ડેટા મુજબ, આજે વેરાવળમાં વરસાદની 97 ટકા શક્યતા સાથે તાપમાન લગભગ 28 ડિગ્રી સેલ્સિયસ છે."*

### Scenario 3: Memory Location Fallback:
- **User**: *"What's the weather today?"*
- **Agent**: *(Detects stored user profile with location `Veraval`)* -> *"For your saved location Veraval, today's temperature is around 28 degrees Celsius with overcast skies."*

### Scenario 4: Weather API Failure Handling (Simulated Timeout):
- **User**: *"What's the weather in Ahmedabad?"* -> *(Simulated API failure/timeout)*
- **Spoken Response**: *"Sorry, I couldn't retrieve the latest weather information right now. Please try again in a moment."*

### Scenario 5: Proactive 6-Step Outbound Weather Alert & Opt-Out:
1. 📞 **Phone Rings** $\rightarrow$ Callee answers call on Linphone.
2. 👋 **Opening Greeting**: *"Hello Gautam, this is Bharat Voice AI. I'm calling with a weather update for your saved location Veraval..."*
3. 🗣️ **Follow-up Question**: Callee asks: *"Will it rain tomorrow in Veraval?"* $\rightarrow$ Agent responds: *"Tomorrow in Veraval, expect 27°C with high rain probability."*
4. 🚫 **Opt-Out Request**: Callee says: *"Don't call me again"*.
5. 👋 **Confirmation**: Agent responds: *"Understood Gautam. I have updated your preferences and will not place future alert calls to you."*
6. 📴 **Call Ends**: Agent invokes `end_call()` tool and automatically disconnects the call session.

---

## 🔒 Security & Privacy Rules

- **Secrets Handling**: All secrets, API keys, and SIP credentials are loaded strictly from environment variables (`.env.local`). Secrets are never committed or logged.
- **User Consent**: User profiles, names, and saved locations are persisted in SQLite only after explicit user verbal consent.
- **Outbound Consent**: Outbound phone call alerts are placed strictly when `outbound_call_consent == True`.
- **Immediate Opt-Out**: Upon opt-out (*"Don't call me again"*), consent is set to `False` in SQLite and call alerts stop immediately.

---

## 🌐 Community & Challenge Attribution

Built as part of the **10 Days of AI Voice Agents — Voice for Bharat Edition** challenge powered by **Murf Falcon** text-to-speech technology.

Hashtags: `#10DaysofAIVoiceAgents` `#MurfFalcon` `#VoiceForBharat`

---

## 📜 License

Built for the **Voice for Bharat Challenge 2026** powered by [Murf AI](https://murf.ai/).
