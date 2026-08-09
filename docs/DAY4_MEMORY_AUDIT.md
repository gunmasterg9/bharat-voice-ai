# Day 4 Memory Architecture & Root Cause Audit — Bharat Voice AI

**Date:** 2026-08-09  
**Auditor:** Senior Voice & Database AI Systems Engineer  
**Project:** Bharat Voice AI (Day 4 Persistent Conversational Memory Task)

---

## 1. System Overview & Component Mapping

Bharat Voice AI is an end-to-end multilingual AI Voice Assistant. The project maps persistent memory across four distinct architectural layers:

```
[ FRONTEND LAYER ]
  Browser localStorage ('bharat_voice_user_id')
       │
       ▼  HTTP POST /api/token?userId=caller_xxx
[ TOKEN GATEWAY LAYER ]
  Next.js API Route (/api/token) -> Mints LiveKit JWT with participantIdentity = 'caller_xxx'
       │
       ▼  WebRTC Room Connection
[ LIVEKIT AGENT LAYER ]
  Python AgentServer -> rtc_session handler in backend/src/agent.py
  Resolves participant.identity -> user_id = 'caller_xxx'
       │
       ▼  SQLite Query
[ PERSISTENT STORAGE LAYER ]
  SQLite Database at project_root/backend/data/bharat_voice.db
  Table: `users` (id, user_id, name, language_preference, facts, created_at, updated_at, last_interaction)
```

---

## 2. Component-by-Component Audit Findings

### 2.1 Frontend Layer (`frontend/components/app/app.tsx`)
- **User ID Generation**: Uses `localStorage.getItem('bharat_voice_user_id')`. If missing, generates `caller_<random>` once and persists it in `localStorage`.
- **Token Endpoint Call**: Appends `userId` to `/api/token?userId=${encodeURIComponent(activeUserId)}`.
- **Persistence Verification**: Survives page reloads, browser restarts, and disconnects.

### 2.2 Token Gateway (`frontend/app/api/token/route.ts`)
- **Query / Body Extraction**: Extracts `searchParams.get('userId')` or `body?.userId`.
- **Participant Identity Assignment**: Mints LiveKit JWT AccessToken setting `identity = requestedUserId`.

### 2.3 Agent Session Handler (`backend/src/agent.py`)
- **Participant Identity Extraction**: Listens for WebRTC room participant join.
- **Retry Mechanism**: Implements an `asyncio.sleep` retry loop (15 retries @ 200ms = 3.0s max) to wait for WebRTC peer connection signal and resolve `participant_identity`.
- **Database Lookup**: Queries `MemoryService.get_user(user_id)` on startup.
- **Dynamic Context Injection**: Appends `[RECOGNIZED RETURNING CALLER PROFILE]` to `voice_agent.instructions` when a profile is found.

### 2.4 Persistent Database Layer (`backend/src/memory/database.py` & `memory_service.py`)
- **Database Location**: Absolute path resolving to `PROJECT_ROOT/backend/data/bharat_voice.db`.
- **Schema**:
  ```sql
  CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT UNIQUE NOT NULL,
      name TEXT,
      language_preference TEXT,
      facts TEXT DEFAULT '{}',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      last_interaction TEXT NOT NULL
  );
  ```
- **PRAGMA Settings**: `PRAGMA journal_mode=WAL;` and `PRAGMA foreign_keys=ON;` for concurrent safety.
- **Transaction Commit**: Explicit transaction boundaries (`BEGIN TRANSACTION;` ... `COMMIT;`).

### 2.5 Agent Tools & Consent Layer (`backend/src/agent/voice_agent.py`)
- **`lookup_caller(user_id)`**: Queries SQLite for caller profile. Placeholder IDs (`"anonymous"`, `"user"`, `"default_user"`) sanitize to `self.user_id`.
- **`save_caller_memory(user_id, name, language_preference, facts, user_consent)`**: Persists profile details ONLY when `user_consent=True`.
- **`forget_caller(user_id, user_confirmation)`**: Completely deletes user row from SQLite when `user_confirmation=True`.
- **Data Scrubbing**: `sanitize_facts()` scrubs passwords, OTPs, PINs, bank accounts, card numbers, ID numbers, and medical notes.

---

## 3. Discovered Failure Modes & Corrections

| ID | Potential Failure Mode | Root Cause | Implemented Resolution |
|---|---|---|---|
| **A** | New User ID Generated Every Call | Fallback to random `uuid.uuid4()` or random room name if participant was slow to join WebRTC room | Implemented 3.0s `asyncio.sleep` retry loop in `agent.py` to guarantee persistent identity capture from LiveKit participant context. |
| **B** | LLM Tool Calls Placeholder Strings | LLM passing literal `"anonymous"` or `"user"` to memory tools | Added string sanitization in `lookup_caller`, `save_caller_memory`, and `forget_caller` mapping placeholders directly to `self.user_id`. |
| **C** | Missing Language Preference | LLM calling `save_caller_memory` without passing `language_preference` argument | Implemented auto-detection fallback in `save_caller_memory` inferring language from recent spoken turns in session memory. |
| **D** | Uncommitted Transactions | SQLite connection remaining uncommitted or using in-memory fallbacks | Added explicit `BEGIN TRANSACTION;` / `COMMIT;` blocks in `database.py` and `update_user_profile`. |

---

## 4. Proposed Corrected Architecture

1. **Frontend**: Persist `localStorage['bharat_voice_user_id']` permanently.
2. **Gateway**: Issue LiveKit JWT with `identity = localStorage.getItem('bharat_voice_user_id')`.
3. **Backend Agent**: Resolve participant identity -> Query SQLite -> Inject recognized profile into `instructions` -> Speak personalized native greeting.
4. **Tools**: Require explicit consent before SQLite writes/deletes.
5. **Persistence**: Disk-backed SQLite database at `backend/data/bharat_voice.db`.
