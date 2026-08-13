# Day 8 — Call Analytics Dashboard Architecture & Documentation

## Executive Overview
Day 8 introduces **Real Call Analytics** for Bharat Voice AI built directly on top of actual call data stored in the central SQLite database (`backend/data/bharat_voice.db`).

The dashboard displays three core operational metrics without fake or hardcoded values:
1. **Total Calls**: Total voice sessions recorded (`COUNT(*)`).
2. **Successful Calls**: Voice calls where the user's primary request completed successfully (`COUNT(outcome = 'SUCCESS')`).
3. **Failed Calls**: Voice calls where the task failed, a required tool errored out, or the conversation ended without completing an objective (`COUNT(outcome != 'SUCCESS')`).

---

## 1. Call Lifecycle & Intent Tracking Architecture

```
Browser UI / Linphone SIP
           │
           ▼
     LiveKit Room
           │
           ▼
 Bharat Voice AI Agent
   (bharat_voice_session)
           │
   ┌───────┴────────┐
   │ record_call_start()  --> outcome: INCOMPLETE
   │ Intent & Tool Tracking (Weather, Memory, Escalation)
   │ record_call_end()    --> outcome: SUCCESS / FAILED / INCOMPLETE / ERROR
   └───────┬────────┘
           │
           ▼
     SQLite Database (calls table)
           │
   ┌───────┴────────┐
   │ GET /api/analytics/summary
   │ GET /api/analytics/calls
   └───────┬────────┘
           │
           ▼
   Call Analytics Dashboard (/analytics, /dashboard)
```

---

## 2. SQLite Database Schema (`calls` table)

Database Path: `backend/data/bharat_voice.db`

```sql
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id TEXT UNIQUE NOT NULL,
    user_id TEXT,
    channel TEXT NOT NULL,          -- 'BROWSER' or 'SIP'
    language TEXT,                  -- 'English', 'Hindi', 'Gujarati'
    started_at TEXT NOT NULL,       -- ISO 8601 UTC timestamp
    ended_at TEXT,                  -- ISO 8601 UTC timestamp
    duration_seconds INTEGER,       -- Calculated call duration
    outcome TEXT NOT NULL,          -- 'SUCCESS', 'FAILED', 'INCOMPLETE', 'ERROR'
    success_reason TEXT,            -- Reason if SUCCESS
    failure_reason TEXT,            -- Reason if FAILED / ERROR
    tool_used TEXT,                 -- Tool invoked during call ('get_weather', 'save_caller_memory', 'create_escalation')
    escalation_created INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
```

---

## 3. Success vs Failure Definition (Day 2 Rules)

### Successful Call (`outcome = 'SUCCESS'`)
A call is classified as **SUCCESSFUL** when the user's primary objective is completed:
- **Weather Request**: User asks for weather and `get_weather` tool returns valid forecasts.
- **Memory Request**: User provides information with explicit consent and profile is saved to SQLite via `save_caller_memory`.
- **Human Help / Escalation**: User requests human assistance, gives permission, and a reference ID (e.g. `ESC-20260813-0001`) is saved to SQLite.
- **Outbound Alert**: Outbound call delivers alert or updates consent upon request.

### Failed / Incomplete Call (`outcome != 'SUCCESS'`)
A call is classified as **FAILED** or **INCOMPLETE** when:
- The intended task was not completed.
- The required tool failed or lacked required arguments/permissions.
- The user hung up before task completion.
- A system or API error occurred.

> [!NOTE]
> The three-number dashboard aggregates metrics as:
> - `total_calls = COUNT(*)`
> - `successful_calls = COUNT(outcome = 'SUCCESS')`
> - `failed_calls = COUNT(outcome != 'SUCCESS')`

---

## 4. Analytics REST API Endpoints

### `GET /api/analytics/summary`
Returns high-level summary totals directly from SQLite:
```json
{
  "success": true,
  "total_calls": 12,
  "successful_calls": 8,
  "failed_calls": 4
}
```

### `GET /api/analytics/calls?limit=50`
Returns recent safe operational call records (excluding credentials and full transcripts):
```json
{
  "success": true,
  "calls": [
    {
      "call_id": "voice_assistant_room_1234",
      "user_id": "caller_a1b2c3d4",
      "channel": "BROWSER",
      "language": "Hindi",
      "started_at": "2026-08-13T13:42:00.000Z",
      "ended_at": "2026-08-13T13:43:22.000Z",
      "duration_seconds": 82,
      "outcome": "SUCCESS",
      "success_reason": "Weather data retrieved for 'Veraval'",
      "failure_reason": null,
      "tool_used": "get_weather",
      "escalation_created": 0
    }
  ]
}
```

---

## 5. Privacy & Security Guarantees
- No passwords, OTPs, PINs, bank numbers, or medical details are recorded or returned.
- Full conversation transcripts are never exposed in the public analytics API.
- Call IDs are unique room/call identifiers without sensitive tokens.

---

## 6. Automated & Live Verification

### Automated Unit Tests
Run backend analytics test suite:
```bash
uv run pytest tests/test_analytics.py
```

### Real Call Demonstration
1. Open the dashboard at `http://localhost:3000/analytics`.
2. Initiate a real browser call and ask for weather in Veraval.
3. Upon call disconnect, the dashboard auto-refreshes every 5 seconds.
4. Total Calls increases by 1, Successful Calls increases by 1.

---

## 7. Known Limitations
- SQLite concurrent write access is safely handled via WAL journal mode, but high multi-threaded concurrency (>100 active connections) would benefit from PostgreSQL in enterprise production deployments.
- Call duration calculation relies on client/server ISO timestamps; clock drift on un-synced host devices could alter duration measurements slightly.

