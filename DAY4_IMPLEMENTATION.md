# Day 4 Implementation Plan — Bharat Voice AI

## 1. Existing Architecture Analysis

- **Framework**: Built on LiveKit Agents SDK (`~1.4`) using `AgentServer` and `AgentSession`.
- **Backend structure**:
  - `backend/src/agent.py`: Entrypoint initializing `AgentServer`, `AgentSession`, STT/LLM/TTS, and Silero VAD.
  - `backend/src/agent/voice_agent.py`: `BharatVoiceAgent` (extends LiveKit `Agent`), manages tools (`get_weather`, `get_latest_news`, `translate_text`), silence handling, language detection, and guardrails.
  - `backend/src/agent/memory.py`: Existing `ConversationMemoryStore` storing JSON session turns in `data/memory/*.json`.
  - `backend/src/agent/prompts.py`: `SYSTEM_PROMPT` containing Day 2 identity, knowledge boundaries, guardrails, and voice rules.
  - `backend/src/agent/guardrails.py`: Input/output filtering engine for safety and prohibited claims.
  - `backend/src/agent/language.py`: Language detection and style mirroring engine.
  - `backend/src/services/`: Services for STT (`DeepgramNova3`), LLM (`GoogleGemini`), TTS (`MurfFalcon`).
- **Frontend structure**:
  - `frontend/app/api/token/route.ts`: API endpoint generating LiveKit JWT access tokens.
  - `frontend/components/app/`: App controller, welcome view, and UI components.
  - `frontend/app-config.ts`: Branding and configuration.

## 2. Voice Pipeline & Tools Baseline

- **STT**: Deepgram Nova-3 (`model="nova-3"`, `language="multi"`).
- **LLM**: Gemini (`gemini-2.5-flash` or `gemini-1.5-flash`).
- **TTS**: Murf Falcon (`livekit-murf`).
- **Turn Detector**: `MultilingualModel()`.
- **Existing Tools**: `get_weather`, `get_latest_news`, `translate_text`.

## 3. Frontend Flow Baseline

- User accesses Next.js frontend -> Clicks "Start Conversation".
- Frontend fetches LiveKit connection token from `/api/token`.
- LiveKit WebRTC session connects participant to `AgentServer`.
- Voice pipeline streams audio bidirectionally.

## 4. Proposed Memory Architecture (Day 4)

- **Database**: Embedded SQLite database located at `backend/data/bharat_voice.db`.
- **Database Layer**: `backend/src/memory/database.py` with WAL journal mode, parameterized SQL queries, connection context managers, and auto-creation of tables/dirs.
- **Memory Service**: `backend/src/memory/memory_service.py` providing CRUD interface:
  - `get_user(user_id)`
  - `save_user(user_id, name, language_preference, facts)`
  - `update_user_facts(user_id, facts)`
  - `update_language_preference(user_id, language)`
  - `update_last_interaction(user_id)`
  - `delete_user(user_id)`
- **Integration Layer**: `backend/src/memory/memory_tools.py` & `BharatVoiceAgent` tool definitions (`lookup_caller`, `save_caller_memory`, `forget_caller`).

## 5. Database Schema

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    language_preference TEXT,
    facts TEXT, -- JSON string
    last_interaction TEXT, -- ISO 8601 timestamp with timezone
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

Example JSON object in `facts`:
```json
{
    "preferred_topic": "technology",
    "location": "Ahmedabad",
    "communication_style": "Hindi-English"
}
```

## 6. User Identification Strategy

1. **Frontend Persistence**: The frontend will generate a persistent `userId` stored in browser `localStorage` (e.g. `bharat_user_id`), and pass it in the request payload to `/api/token`.
2. **Token Generation**: `/api/token` uses `body.userId` as `participantIdentity`.
3. **LiveKit Session Context**: When the session starts in `agent.py`, `ctx.room.remote_participants` or session participant identity is extracted. If absent or in console mode, defaults to `default_user`.
4. **ID Scoping**: Every database lookup and mutation is strictly parameterized by `user_id` to prevent cross-user data leakage.

## 7. Privacy & Consent Flow

- **Zero Silent Persistence**: Facts, names, and language preferences are stored ONLY after explicit user consent.
- **Consent States**: `UNKNOWN`, `GRANTED`, `DENIED`.
- **Negative Consent**: If user says "No", "Don't save", "Don't remember", state becomes `DENIED`. Acknowledge gracefully ("Of course. I won't save that information.") and DO NOT persist.
- **Sensitive Facts Filter**: Strict refusal to save sensitive credentials (passwords, OTPs, PINs, bank accounts, credit cards, API keys).
- **Forget-Me Protocol**: "Forget me" triggers explicit confirmation prompt before calling `delete_user(user_id)`.

## 8. Files to Modify & Create

### New Files to Create:
- `backend/src/memory/__init__.py`
- `backend/src/memory/database.py`
- `backend/src/memory/memory_service.py`
- `backend/tests/test_memory.py`
- `DAY4_IMPLEMENTATION.md`
- `MEMORY_RED_TEAM.md`
- `docs/DAY4.md`

### Files to Modify:
- `backend/src/agent/voice_agent.py` (Add memory tools: `lookup_caller`, `save_caller_memory`, `forget_caller`, load profile on startup)
- `backend/src/agent/prompts.py` (Update `SYSTEM_PROMPT` for privacy rules, returning caller guidelines, Devanagari Hindi / Gujarati script requirements)
- `backend/src/agent.py` (Extract participant identity for session user ID)
- `frontend/app/api/token/route.ts` (Accept `userId` from POST payload for participant identity)
- `frontend/components/app/app.tsx` & UI (Pass `userId` from `localStorage`, display subtle memory status badge)
- `README.md` (Document Day 4 features, schema, tools, security, testing)
