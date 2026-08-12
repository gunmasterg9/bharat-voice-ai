# Day 7 — Know When to Ask for Human Help

## Objective

Bharat Voice AI is designed to recognize when a problem cannot be safely or reliably handled autonomously. In such cases, the agent gracefully transitions to a human support protocol by:

1. Detecting the need for human assistance.
2. Explaining why human help is required.
3. Explaining what information will be shared with the human team.
4. Requesting explicit user permission before creating an escalation request.
5. Invoking the `create_escalation` tool upon receiving permission.
6. Generating a unique dynamic reference ID (`ESC-YYYYMMDD-XXXX`).
7. Providing honest next-step expectations to the caller without false promises.
8. Exposing all escalation cases in a dedicated Human Help Dashboard.
9. Allowing human operators to manage case status (`OPEN` → `IN_PROGRESS` → `RESOLVED`).

---

## Escalation Triggers

### Trigger 1: Weather Data Unavailable
When the real-time weather service (`Open-Meteo API`) experiences timeouts, HTTP errors, service unavailability, or cannot provide reliable data for a requested location:
- The agent **never** invents current weather or temperature data.
- The agent informs the user that live weather information is currently unavailable.
- The agent offers to create a human-help request and asks for permission before doing so.

#### Example (Gujarati):
> **User**: "વેરાવળમાં અત્યારે હવામાન કેવું છે?"  
> **Agent**: "હું હાલમાં વિશ્વસનીય હવામાન માહિતી મેળવી શકતો નથી. જો તમે ઇચ્છો તો હું માનવ સહાય માટે વિનંતી બનાવી શકું."

### Trigger 2: Explicit User Help Request
When the caller explicitly asks to speak to a person or human support agent:
- **Phrases**: "Can I talk to a human?", "I need a person to help me", "મારે કોઈ વ્યક્તિ સાથે વાત કરવી છે", "મને માનવ સહાય જોઈએ છે", "आप मुझे किसी इंसान से जोड़ सकते हैं?"
- The agent initiates the permission flow.
- The agent **does not** immediately create the request without explicit consent.

---

## Permission & Consent Flow

Before calling `create_escalation`, the agent **must**:
1. Explain **why** human help is needed.
2. Explain **what** information will be shared (name, problem description, what was checked, preferred language, urgency).
3. Ask for explicit user permission.
4. Wait for a clear positive answer.

### Sample Consent Explanation (English):
> "I can create a request for human assistance. I would share your name, the problem you described, what I already checked, your preferred language, and the urgency. Is that okay?"

### Permission Granted:
- **Inputs**: "Yes", "Yes please", "Okay", "હા", "હા, કરો", "हाँ", "जरूर".
- **Action**: Agent invokes `create_escalation(..., user_permission=True)`.
- **Spoken Response**: States reference ID and honest next steps.

### Permission Denied:
- **Inputs**: "No", "Don't share it", "નહીં", "મારી માહિતી શેર ન કરો", "मेरी जानकारी शेयर मत करो".
- **Action**: Agent **does not** call `create_escalation`. No database record is created.
- **Spoken Response**: Polite acknowledgment ("Understood. I will not create a human help request.").

---

## Human Help Tool (`create_escalation`)

The voice agent is equipped with the `create_escalation` LiveKit `@function_tool`.

### Tool Signature:
```python
@function_tool
async def create_escalation(
    context: RunContext,
    reason: str,
    summary: str,
    what_was_checked: str | None = None,
    urgency: str = "LOW",
    preferred_follow_up: str | None = "phone",
    user_permission: bool = False,
    name: str | None = None,
    language: str | None = None,
) -> str
```

### Response JSON:
```json
{
  "success": true,
  "reference_id": "ESC-20260812-0001",
  "status": "OPEN"
}
```

---

## Privacy Protection & Data Hygiene

To guarantee complete privacy, Bharat Voice AI enforces strict data hygiene rules:

1. **Scrubbing Prohibited Data**: Passwords, OTPs, PINs, bank account numbers, credit/debit card numbers, CVVs, auth tokens, and API credentials are automatically filtered and redacted prior to database insertion.
2. **No Transcript Storage**: Full conversation transcripts are never saved to the escalation record. Only a concise, structured human summary is stored.
3. **Structured Summary Content**:
   - **WHO** needs help (Name & User ID)
   - **WHAT** happened (Reason & Summary)
   - **WHAT** was already checked (Triage/Tools attempted)
   - **URGENCY** level (`LOW`, `MEDIUM`, `HIGH`)
   - **LANGUAGE** preference (Native script register)
   - **PREFERRED FOLLOW-UP** method (Phone call)

---

## Database Schema (`escalations` Table)

Stored in persistent SQLite database (`backend/data/bharat_voice.db`):

```sql
CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT,
    language TEXT,
    reason TEXT NOT NULL,
    summary TEXT NOT NULL,
    what_was_checked TEXT,
    urgency TEXT NOT NULL DEFAULT 'LOW',
    preferred_follow_up TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

---

## Dynamic Reference ID Generation

Format: `ESC-YYYYMMDD-XXXX`
- `ESC`: Standard escalation prefix.
- `YYYYMMDD`: Current UTC date string (e.g. `20260812`).
- `XXXX`: 4-digit zero-padded daily incremental sequence counter (e.g. `0001`, `0002`).

---

## Human Help Dashboard UI & API Endpoints

### Frontend Dashboard (`Bharat Voice AI - Human Help`)
Located in Next.js frontend (`frontend/components/HumanHelpDashboard.tsx`).
- **Features**:
  - Live metric counters (Total, Open, In Progress, Resolved).
  - Search & status filter tabs (`ALL`, `OPEN`, `IN_PROGRESS`, `RESOLVED`).
  - Detailed card views showing Reference ID, Urgency badge, Reason, Caller Name, Language, Summary, Checked tools, and Timestamps.
  - Interactive status dropdown menu to transition case status (`OPEN` → `IN_PROGRESS` → `RESOLVED`).

### Backend API Endpoints
- `GET /api/escalations`: Lists escalation records from `bharat_voice.db`.
- `PATCH /api/escalations/[id]`: Updates status with schema validation.

---

## Duplicate Escalation Prevention

If a caller already has an active `OPEN` request in the database for the exact same reason:
- The system prevents creating unnecessary duplicate rows.
- The existing `reference_id` is retrieved and returned to the caller.

---

## Automated Test Coverage

The test suite in `backend/tests/test_escalation.py` verifies all 15 scenarios:

1. `test_normal_conversation_no_escalation`: Verifies normal calls create 0 escalations.
2. `test_explicit_human_request_permission_yes`: Verifies explicit request + YES creates record.
3. `test_weather_failure_escalation`: Verifies weather API failure escalation creation.
4. `test_permission_no_prevents_escalation`: Verifies NO consent blocks DB insertion.
5. `test_reference_id_generation_format`: Verifies `ESC-YYYYMMDD-XXXX` pattern.
6. `test_duplicate_escalation_prevention`: Verifies existing ref ID is returned for duplicates.
7. `test_sensitive_info_filtering`: Verifies passwords, PINs, OTPs, and card numbers are scrubbed.
8. `test_create_escalation_tool_no_permission`: Verifies tool refusal without consent.
9. `test_database_failure_handling`: Verifies graceful failure on DB transaction errors.
10. `test_status_transitions`: Verifies `OPEN` → `IN_PROGRESS` → `RESOLVED` workflow.
11. `test_dashboard_list_and_filter`: Verifies query filtering by status.
12. `test_gujarati_escalation_flow`: Verifies Gujarati native script escalation records.
13. `test_hindi_escalation_flow`: Verifies Hindi native script escalation records.
14. `test_english_escalation_prompt_check`: Verifies `SYSTEM_PROMPT` contains Day 7 rules.

---

## Example Conversations

### Scenario A: Explicit Request with Permission (English)
- **Caller**: "Can I talk to a human?"
- **Agent**: "I can create a request for human assistance. I would share your name, the problem you described, what I already checked, your preferred language, and the urgency. Is that okay?"
- **Caller**: "Yes, please."
- **Agent**: "Your request has been created. Your reference ID is ESC-20260812-0001. A human support operator can review the request. I cannot promise an immediate response, but someone will review it soon."

### Scenario B: Weather Failure with Permission (Gujarati)
- **Caller**: "વેરાવળમાં અત્યારે હવામાન કેવું છે?"
- **Agent**: "હું હાલમાં વિશ્વસનીય હવામાન માહિતી મેળવી શકતો નથી. જો તમે ઇચ્છો તો હું માનવ સહાય માટે વિનંતી બનાવી શકું."
- **Caller**: "હા, કરો."
- **Agent**: "તમારી વિનંતી નોંધાઈ ગઈ છે. તમારો reference ID ESC-20260812-0002 છે. માનવ સહાય ટીમ તમારી વિનંતી જોઈ શકે છે. મને તરત જવાબ મળશે એવું વચન આપી શકાતું નથી."

### Scenario C: Permission Denied (Hindi)
- **Caller**: "मुझे किसी इंसान से बात करनी है।"
- **Agent**: "मैं मानव सहायता के लिए एक अनुरोध बना सकती हूँ। इसमें आपका नाम, समस्या, भाषा और प्राथमिकता साझा की जाएगी। क्या यह ठीक है?"
- **Caller**: "नहीं, मेरी जानकारी शेयर मत करो।"
- **Agent**: "ठीक है। मैं मानव सहायता का अनुरोध दर्ज नहीं करूँगी। क्या मैं आपकी किसी और विषय में मदद कर सकती हूँ?"
