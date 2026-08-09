# Bharat Voice AI — Multilingual Voice Assistant for India 🇮🇳

**Bharat Voice AI** is a production-ready, multilingual conversational AI voice assistant built for Indian users as part of the official **"10 Days of AI Voice Agents | Voice for Bharat Edition"** challenge.

Powered by **Murf Falcon TTS**, **LiveKit Agents SDK**, **Deepgram Nova-3 STT**, **Google Gemini**, and **SQLite Persistent Memory**.

---

## 💾 Day 4: Persistent Conversational Memory & Privacy Controls

Day 4 gives Bharat Voice AI persistent caller memory powered by an embedded SQLite database (`data/bharat_voice.db`) that survives process, terminal, and application restarts while enforcing zero silent persistence and explicit privacy consent rules.

### Key Day 4 Features
- **SQLite Database**: Auto-created SQLite storage at `data/bharat_voice.db` using WAL mode, connection context managers, and 100% parameterized SQL.
- **Strict Privacy Consent Protocol**:
  - Agent asks for explicit verbal/UI permission before saving facts or names (*"Would you like me to remember your name for future conversations?"*).
  - Explicit refusal (*"No"*, *"Don't save"*, *"Don't remember"*) triggers immediate opt-out: *"Of course. I won't save that information."* No data is written.
  - Silence or ambiguous answers ARE NOT consent.
  - **Sensitive Data Blocklist**: Password, PIN, OTP, bank account, credit card, and API key storage attempts are automatically scrubbed and blocked.
- **Agent Tools for Memory**:
  - `lookup_caller`: Retrieves returning caller profile from SQLite without revealing internal database details.
  - `save_caller_memory`: Writes profile to SQLite ONLY after explicit consent (`user_consent=True`).
  - `forget_caller`: Deletes user profile completely from SQLite ONLY after explicit user confirmation (`user_confirmation=True`).
- **Returning Caller Greeting**:
  - Identifies callers across sessions using browser `localStorage` persistent `userId`.
  - Greets returning callers warmly by name: *"Namaste Ramesh! Welcome back. How can I help you today?"* or in Devanagari Hindi (*"नमस्ते Ramesh! आपका स्वागत है।"*).
- **Native Script Enforcement**:
  - Hindi MUST use Devanagari script (e.g. `नमस्ते`), Gujarati uses Gujarati script (`કેમ છો`), and English uses Latin script.
- **Frontend Memory Status Badge**: Subtle UI badge indicating `Memory: Active (Consent-based)`.

---

## 🗄️ SQLite Database Schema

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    language_preference TEXT,
    facts TEXT DEFAULT '{}', -- JSON string
    last_interaction TEXT, -- Timezone-aware ISO 8601 timestamp
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

---

## 🎨 Day 3: Personalized Frontend

- **Voice-First Design**: Large central interactive voice button with smooth micro-animations.
- **Strict 5-State Machine**: `READY`, `CONNECTING`, `LISTENING`, `SPEAKING`, `CALL_ENDED`.
- **Robust Error Recovery**: Handles `PERMISSION_ERROR` and `CONNECTION_ERROR` with clear recovery steps.
- **Live Conversation Transcript**: Compact, collapsible transcript drawer.

---

## 📂 Project Structure

```
murf-livekit-starter/
├── DAY4_IMPLEMENTATION.md    # Day 4 Architecture & Inspection Document
├── MEMORY_RED_TEAM.md        # 18 Red Team Privacy & Security Test Scenarios
├── RED_TEAM.md               # Day 2 Safety Guardrails Attack Scenarios
├── docs/
│   ├── DAY4.md              # Day 4 Architecture & User Documentation
│   └── DAY3.md              # Day 3 Architecture & User Documentation
├── README.md                 # Project Overview & Setup Instructions
├── backend/
│   ├── data/
│   │   └── bharat_voice.db   # Persistent SQLite Database
│   ├── src/
│   │   ├── agent.py          # Orchestrator & Participant ID Resolver
│   │   ├── agent/            # Config, Prompts, Voice Agent, Guardrails, Memory
│   │   ├── memory/           # Database Manager & Memory Service
│   │   └── services/         # Gemini LLM, Deepgram STT, Murf Falcon TTS
│   └── tests/                # Pytest Suite (21/21 Tests Passed)
└── frontend/                 # Next.js Voice UI
    ├── app/api/token/route.ts# Token Route with Persistent UserId
    └── components/           # Voice Agent UI & Memory Status Badge
```

---

## 🧪 Testing

Run full backend test suite (21 unit, integration, and LLM-judged evaluation tests):

```bash
cd backend
uv run pytest
```

Run specific Day 4 persistent memory tests:

```bash
cd backend
uv run pytest tests/test_memory.py
```

---

## ⚡ Quick Start

### 1. Backend Setup

```bash
cd backend
uv sync
uv run python src/agent.py dev
```

### 2. Frontend Setup

```bash
cd frontend
pnpm install
pnpm dev
```

Open `http://localhost:3000` in your browser.

---

## 🗣️ Example Day 4 Demo Flow

### Call 1: Consent & Persistence
- **User**: *"Hello, my name is Ramesh."*
- **Agent**: *"Nice to meet you, Ramesh. Would you like me to remember your name for future conversations?"*
- **User**: *"Yes."* -> *(Agent saves profile to SQLite database)*
- **User**: *"I prefer Hindi."*
- **Agent**: *"Would you like me to save Hindi as your preferred language?"*
- **User**: *"Yes."* -> *(Agent saves preferred language)*

### Call 2: Restart Agent Process & Reconnect Same User ID
- *(Restart backend process completely)*
- **Agent**: *"Namaste Ramesh! Welcome back. How can I help you today?"*

### Call 3: Privacy Opt-Out ("No")
- **User**: *"My name is Amit."*
- **Agent**: *"Would you like me to remember your name for future conversations?"*
- **User**: *"No, don't save that."*
- **Agent**: *"Of course. I won't save that information."* -> *(No data written to SQLite)*

### Call 4: Forget Me Protocol
- **User**: *"Forget everything you know about me."*
- **Agent**: *"I can delete your saved profile and memories. Would you like me to do that?"*
- **User**: *"Yes."* -> *(Agent executes DELETE FROM users WHERE user_id = ?)*
- **Agent**: *"Done. I've removed your saved information."*

---

## 🛣️ Roadmap

- [x] **Day 1**: LiveKit + Murf Falcon + Deepgram + Gemini Voice Pipeline Foundation
- [x] **Day 2**: Multilingual Support (HI, GU, EN, Hinglish, Gujlish), Guardrails Engine, Silence Handling, Session Memory, Red Team Suite
- [x] **Day 3**: Personalized Multilingual Voice Frontend, 5-State Machine, Dual Audio Visualizers, Microphone Permission & Connection Error Handling
- [x] **Day 4**: Persistent Conversational Memory with SQLite, Consent Management, Sensitive Credential Filtering, Native Scripts, Returning Caller Flow, Forget-Me Protocol
