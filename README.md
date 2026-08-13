# Bharat Voice AI — Multilingual Voice Assistant for India 🇮🇳

[![Voice for Bharat Challenge 2026](https://img.shields.io/badge/Voice%20for%20Bharat-Challenge%202026-orange.svg)](https://github.com/murf-ai/voice-for-bharat-challenge-2026)
[![TTS](https://img.shields.io/badge/TTS-Murf%20Falcon%20(~100ms)-blue.svg)](https://murf.ai/falcon)
[![Framework](https://img.shields.io/badge/Framework-LiveKit%20Agents%201.4-green.svg)](https://docs.livekit.io/)
[![Tests](https://img.shields.io/badge/Tests-Passed-brightgreen.svg)]()

## Project Overview

**Bharat Voice AI** is an intelligent, multilingual voice assistant tailored for India, built with **Murf Falcon TTS** (~100ms streaming latency), **Deepgram Nova-3 STT**, **Google Gemini**, and **LiveKit Agents SDK**. It delivers real-time weather forecasts, remembers user preferences with explicit consent in a persistent SQLite database, makes proactive weather alert phone calls over SIP, handles human help escalations, and provides a real-time **Call Analytics Dashboard** driven by live database metrics.

- **Track Selected:** 🌦️ **Weather & Disaster Response** (*Real-Time Weather Voice Assistant, Proactive Alert System & Call Analytics*)
- **Core Problem Solved:** Provides citizens, farmers, and travelers across India with hands-free, spoken access to live weather forecasts, proactive rain & extreme weather phone alert calls, saved location memory, human escalation support, and multilingual voice guidance in native Indian languages (Hindi, Gujarati, Indian English, Hinglish, Gujlish).

---

## Features

### Day 1 Voice Agent
- Configured LiveKit Agents WebRTC voice pipeline with Deepgram STT $\rightarrow$ Gemini LLM $\rightarrow$ Murf Falcon TTS (~100ms latency).
- Configured Indian English (`Anisha`, `Pooja`, `Samar`) voices for low-latency streaming.

### Day 2 Persona, Guardrails and Multilingual Conversation
- **Structured System Prompt:** `IDENTITY`, `OBJECTIVES`, `KNOWLEDGE`, `LANGUAGE`, `GUARDRAILS`, `STYLE`.
- Female persona ("Bharat Voice AI"), native Hindi/Gujarati script agreement rules.
- Strict refusal triggers and standardized escalation script for medical, legal, and financial queries.
- Automatic silence protocol (Turn 1: *"Are you still there?"*, Turn 2: *"Goodbye"*).

### Day 3 Personalized Frontend
- Weather-themed Next.js UI with 5 explicit agent states (`Ready`, `Connecting`, `Listening`, `Speaking`, `Call Ended`).
- Real-time animated audio visualizer waves and status badges.
- Microphone permission error handling and live system logs.

### Day 4 Persistent User Memory
- Disk-backed SQLite storage (`backend/data/bharat_voice.db`) with WAL mode.
- Explicit verbal consent protocol ("Ask before you save") for location preferences and names.
- Persistent caller ID routing across browser restarts.
- Sensitive credential scrubbing (passwords, PINs, bank accounts).

### Day 5 Real Weather Tool
- Real-time Open-Meteo REST API integration for live weather queries.
- Location fallback synergy: automatically retrieves user's saved SQLite location if no city is provided in the query.
- Graceful API failure handling without hallucinations.

### Day 6 Outbound Voice Calls
- Outbound SIP telephony integration via LiveKit Telephony API and Linphone.
- Proactive rain alert trigger based on live weather forecasts.
- 6-step interactive outbound call lifecycle with mandatory 3-part spoken intro and immediate opt-out persistence in SQLite.

### Day 7 Human Escalation
- Autonomous human help detection when problems cannot be solved safely.
- Explicit user permission flow and dynamic reference ID generation (`ESC-YYYYMMDD-XXXX`).
- Next.js Operator Dashboard with status filter tabs (`ALL`, `OPEN`, `IN_PROGRESS`, `RESOLVED`).

### Day 8 Call Analytics Dashboard
- Real call metrics calculated directly from SQLite database:
  - **TOTAL CALLS**: `COUNT(*)` across Browser and SIP channels.
  - **SUCCESSFUL CALLS**: `COUNT(outcome = 'SUCCESS')` where user's primary intent completed.
  - **FAILED CALLS**: `COUNT(outcome != 'SUCCESS')` for incomplete, failed, or error calls.
- Multi-channel support tracking both Browser and SIP voice calls.
- Privacy protection ensuring operational logs contain no credentials, OTPs, or full conversation transcripts.

---

## Architecture

```
Frontend ↓ LiveKit ↓ Deepgram ↓ Gemini ↓ Tools ↓ SQLite / External APIs ↓ Murf Falcon
```

### Detailed Pipeline Flow:
1. **Frontend / SIP Client**: Captures microphone audio stream over WebRTC / SIP.
2. **LiveKit Agent Server**: Routes real-time audio streams between client and pipeline worker.
3. **Deepgram Nova-3**: Converts spoken audio to text in real time.
4. **Google Gemini**: Processes natural language prompt, guardrails, and intent.
5. **Tools**:
   - `get_weather`: Open-Meteo REST API for live weather forecasts.
   - SQLite Database: `users`, `outbound_calls`, `escalations`, `calls` tables.
6. **Murf Falcon TTS**: Converts response text into high-fidelity Indian audio (~100ms streaming).

---

## Setup

### 1. Clone repository
```bash
git clone https://github.com/gunmasterg9/bharat-voice-ai.git
cd bharat-voice-ai
```

### 2. Create virtual environment
```bash
cd backend
uv venv
```

### 3. Install dependencies
```bash
# Backend dependencies
cd backend
uv sync

# Frontend dependencies
cd ../frontend
pnpm install
```

### 4. Create .env files
Copy template files to create local environment configurations:
```bash
cp backend/.env.example backend/.env.local
cp frontend/.env.example frontend/.env.local
```

### 5. Add required credentials
Fill in your API credentials inside `backend/.env.local` and `frontend/.env.local`:
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- `MURF_API_KEY`
- `DEEPGRAM_API_KEY`
- `GOOGLE_API_KEY`
- `LIVEKIT_SIP_OUTBOUND_TRUNK_ID`, `LINPHONE_USERNAME` *(Optional for SIP calling)*

### 6. Start backend
```bash
cd backend
uv run python src/agent.py dev
```

### 7. Start frontend
```bash
cd frontend
pnpm dev
```

### 8. Open dashboard
Open your browser to:
- Voice UI: `http://localhost:3000`
- Analytics Dashboard: `http://localhost:3000/analytics` or click the **Analytics** tab in the top header bar.

---

## Testing

Run tests across all project modules to verify system health:

### Voice & Agent Pipeline Testing
```bash
cd backend
uv run python src/agent.py console
```

### Memory Testing
```bash
cd backend
uv run pytest tests/test_agent.py
```

### Weather Tool Testing
```bash
cd backend
uv run pytest tests/test_weather_tool.py
```

### Escalation Testing
```bash
cd backend
uv run pytest tests/test_escalation.py
```

### Outbound SIP Testing
```bash
cd backend
uv run pytest tests/test_6step_outbound_flow.py
```

### Analytics Testing
```bash
cd backend
uv run pytest tests/test_analytics.py
```

---

## 🔒 Security & Privacy

- All secrets, API keys, and SIP credentials are loaded strictly from `.env.local` files and are never committed.
- Database operational metrics contain no sensitive personal data or credentials.
- User memories and outbound call consents require explicit user verbal consent.
- **Outbound Consent**: Outbound phone call alerts are placed strictly when `outbound_call_consent == True`.
- **Immediate Opt-Out**: Upon opt-out (*"Don't call me again"*), consent is set to `False` in SQLite and call alerts stop immediately.
- **Analytics Privacy**: Dashboard displays operational metrics only. No passwords, OTPs, PINs, bank details, or full conversation transcripts are stored or exposed.

---

## 🌐 Community & Challenge Attribution

Built as part of the **10 Days of AI Voice Agents — Voice for Bharat Edition** challenge powered by **Murf Falcon** text-to-speech technology.

Hashtags: `#10DaysofAIVoiceAgents` `#MurfFalcon` `#VoiceForBharat`

---

## 📜 License

Built for the **Voice for Bharat Challenge 2026** powered by [Murf AI](https://murf.ai/).

