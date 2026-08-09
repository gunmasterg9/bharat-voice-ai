# Day 4 - Give Your Agent a Memory That Lasts

**Project:** Bharat Voice AI  
**Status:** **DAY 4 MEMORY SYSTEM COMPLETE & VERIFIED**

---

## 1. Overview & Architecture

Day 4 equips **Bharat Voice AI** with real, persistent, disk-backed conversational memory using SQLite. Information (caller name, language preference, and domain-track facts) survives:
- End of LiveKit calls
- Page reloads
- Python agent process restarts
- Server or system restarts

```text
Browser localStorage ('bharat_voice_user_id')
       │
       ▼  HTTP GET/POST /api/token?userId=caller_xxx
Next.js Token Gateway (Mints LiveKit JWT with participantIdentity = 'caller_xxx')
       │
       ▼  WebRTC Room Peer Connection
Python Agent Server (agent.py resolves participant.identity -> user_id = 'caller_xxx')
       │
       ▼  SQLite Query
Disk Database (project_root/backend/data/bharat_voice.db)
```

---

## 2. Persistent User ID Flow

1. **Frontend Persistence**: `localStorage.getItem('bharat_voice_user_id')` generates a unique string once (`caller_<hex>`) and retains it across browser reloads.
2. **Gateway**: Passes `userId` to `/api/token`, setting `participantIdentity` in the LiveKit JWT token.
3. **Agent Resolution**: `agent.py` reads `participant.identity` from `ctx.room.remote_participants` with a 3.0-second async retry loop.

---

## 3. SQLite Database & Schema

- **Path**: `backend/data/bharat_voice.db`
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

---

## 4. Memory Tools & Explicit Consent Protocol

- `lookup_caller`: Fetches profile by `user_id`.
- `save_caller_memory`: Persists profile to SQLite **ONLY IF `user_consent=True`**.
- `forget_caller`: Deletes SQLite profile row **ONLY IF `user_confirmation=True`**.

---

## 5. Security & Refusal Rules

The memory service enforces sensitive keyword sanitization:
- **Blocked Items**: Passwords, PINs, OTPs, Aadhaar/PAN/Voter IDs, bank account numbers, credit card numbers, and written medical notes.
- **Refusal Message**: *"I can't store sensitive credentials such as passwords, PINs, or OTPs."*

---

## 6. Verification Commands

```bash
# Run backend persistent memory automated test suite:
cd backend
uv run pytest tests/test_persistent_memory.py

# Inspect SQLite database records on disk:
cd backend/src
..\.venv\Scripts\python.exe -m memory.inspect_db
```
