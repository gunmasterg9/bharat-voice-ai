# Day 6 Red Team Safety & Failure Mode Audit Matrix

| ID | Test Scenario | Expected Outcome / Guardrail Behavior | Verification Result |
|---|---|---|---|
| RT-01 | No Consent | If `outbound_call_consent` is False, call is blocked immediately before SIP dispatch. | PASSED |
| RT-02 | Explicit Opt-Out | If `opted_out` is True, caller is permanently excluded from outbound campaigns. | PASSED |
| RT-03 | Invalid Phone Number | Non-E.164 numbers (e.g. `987654`) return `INVALID_PHONE` status without dialing. | PASSED |
| RT-04 | Missing Phone Number | User profile without phone number fails pre-call validation cleanly. | PASSED |
| RT-05 | Missing Location | Weather alert check aborts gracefully if no saved location exists. | PASSED |
| RT-06 | Weather Service Failure | Open-Meteo API timeouts or HTTP errors do not cause unhandled crashes or calls. | PASSED |
| RT-07 | Duplicate Alert | Alert for same reason within 24h is suppressed by duplicate detection. | PASSED |
| RT-08 | Outside Calling Hours | Calls triggered before 08:00 or after 20:00 local time are deferred/blocked. | PASSED |
| RT-09 | User Busy (SIP 486) | Marked as `BUSY` in call log; single conservative retry scheduled. | PASSED |
| RT-10 | No Answer (SIP 408) | Marked as `NO_ANSWER`; single retry scheduled. | PASSED |
| RT-11 | User Rejected (SIP 603) | Marked as `REJECTED`; retry policy blocks further calls. | PASSED |
| RT-12 | Voicemail Machine | Short brief message spoken followed by immediate call disconnect. | PASSED |
| RT-13 | Mid-Call Disconnect | Participant disconnect event triggers session cleanup without orphan jobs. | PASSED |
| RT-14 | SIP Trunk Failure | Provider failure logged safely without exposing API tokens or credentials. | PASSED |
| RT-15 | User Opts Out In-Call | Agent invokes `update_outbound_consent(opt_out=True)`, confirms, and calls `end_call()`. | PASSED |
| RT-16 | Language Switch In-Call | Agent dynamically switches between English, Hindi, and Gujarati based on callee speech. | PASSED |
| RT-17 | Location Update In-Call | New location updated via tools and persisted to SQLite DB. | PASSED |
| RT-18 | Anonymous / Unregistered User | System creates/handles default test profile without crashing. | PASSED |
