"""
Bharat Voice AI — Analytics Service Module

Manages persistent call lifecycle tracking and metrics in SQLite (calls table).
Provides functions:
- record_call_start()
- record_call_end()
- get_call_metrics()
- get_recent_calls()
"""

from datetime import datetime, timezone
from typing import Any

from agent.logger import COMPONENT_AGENT, get_logger
from memory.database import Database, get_db

logger = get_logger(COMPONENT_AGENT)

ALLOWED_OUTCOMES = {"SUCCESS", "FAILED", "INCOMPLETE", "ERROR"}
ALLOWED_CHANNELS = {"BROWSER", "SIP"}


class AnalyticsService:
    """Service to handle call analytics tracking and querying."""

    def __init__(self, db: Database | None = None) -> None:
        self.db = db or get_db()

    def record_call_start(
        self,
        call_id: str,
        user_id: str = "default_user",
        channel: str = "BROWSER",
        language: str | None = None,
    ) -> dict[str, Any]:
        """
        Record the start of a call. Initial outcome is INCOMPLETE.
        Guarantees idempotent insertion without duplicate error.
        """
        if not call_id:
            raise ValueError("call_id cannot be empty")

        channel_clean = str(channel or "BROWSER").strip().upper()
        if channel_clean not in ALLOWED_CHANNELS:
            channel_clean = "BROWSER"

        now_iso = datetime.now(timezone.utc).isoformat()

        query = """
        INSERT INTO calls (
            call_id, user_id, channel, language, started_at, outcome, created_at
        ) VALUES (?, ?, ?, ?, ?, 'INCOMPLETE', ?)
        ON CONFLICT(call_id) DO UPDATE SET
            user_id = excluded.user_id,
            channel = excluded.channel,
            language = COALESCE(excluded.language, calls.language);
        """
        params = (call_id, user_id, channel_clean, language, now_iso, now_iso)
        self.db.execute_write(query, params)

        logger.info(
            "[ANALYTICS] Call started | Call ID: %s | Channel: %s | User ID: %s",
            call_id,
            channel_clean,
            user_id,
        )
        return {
            "call_id": call_id,
            "user_id": user_id,
            "channel": channel_clean,
            "language": language,
            "started_at": now_iso,
            "outcome": "INCOMPLETE",
        }

    def record_call_end(
        self,
        call_id: str,
        outcome: str,
        success_reason: str | None = None,
        failure_reason: str | None = None,
        tool_used: str | None = None,
        escalation_created: int = 0,
        language: str | None = None,
        ended_at: str | None = None,
    ) -> dict[str, Any]:
        """
        Record the end of a call and update outcome, duration, and metrics.
        Idempotent: updates existing call record or inserts if missing.
        """
        if not call_id:
            raise ValueError("call_id cannot be empty")

        outcome_clean = str(outcome or "INCOMPLETE").strip().upper()
        if outcome_clean not in ALLOWED_OUTCOMES:
            outcome_clean = "FAILED"

        now_dt = datetime.now(timezone.utc)
        ended_iso = ended_at or now_dt.isoformat()

        # Retrieve existing call record to compute duration
        existing = self.db.execute_read(
            "SELECT started_at, language FROM calls WHERE call_id = ? LIMIT 1;",
            (call_id,),
        )

        duration_seconds = 0
        if existing and existing[0]["started_at"]:
            try:
                start_dt = datetime.fromisoformat(existing[0]["started_at"])
                duration_seconds = max(0, int((now_dt - start_dt).total_seconds()))
            except Exception:
                duration_seconds = 0
        else:
            # If start was not recorded, record call start timestamp as now
            self.record_call_start(
                call_id=call_id,
                channel="BROWSER",
                language=language,
            )

        final_lang = language or (existing[0]["language"] if existing else None)

        update_query = """
        UPDATE calls
        SET ended_at = ?,
            duration_seconds = ?,
            outcome = ?,
            success_reason = ?,
            failure_reason = ?,
            tool_used = ?,
            escalation_created = ?,
            language = COALESCE(?, language)
        WHERE call_id = ?;
        """
        params = (
            ended_iso,
            duration_seconds,
            outcome_clean,
            success_reason,
            failure_reason,
            tool_used,
            1 if escalation_created else 0,
            final_lang,
            call_id,
        )
        self.db.execute_write(update_query, params)

        logger.info(
            "[ANALYTICS] Call ended | Call ID: %s | Outcome: %s | Duration: %ds",
            call_id,
            outcome_clean,
            duration_seconds,
        )
        return {
            "call_id": call_id,
            "outcome": outcome_clean,
            "duration_seconds": duration_seconds,
            "success_reason": success_reason,
            "failure_reason": failure_reason,
            "tool_used": tool_used,
            "escalation_created": 1 if escalation_created else 0,
        }

    def get_call_metrics(self) -> dict[str, int]:
        """
        Get aggregated call analytics summary.
        Calculates:
        - total_calls = COUNT(*)
        - successful_calls = COUNT(outcome = 'SUCCESS')
        - failed_calls = COUNT(outcome != 'SUCCESS')
        """
        query = """
        SELECT
            COUNT(*) as total_calls,
            SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) as successful_calls,
            SUM(CASE WHEN outcome != 'SUCCESS' THEN 1 ELSE 0 END) as failed_calls
        FROM calls;
        """
        rows = self.db.execute_read(query)
        if not rows or rows[0]["total_calls"] is None:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
            }

        total = rows[0]["total_calls"] or 0
        success = rows[0]["successful_calls"] or 0
        failed = rows[0]["failed_calls"] or 0

        return {
            "total_calls": int(total),
            "successful_calls": int(success),
            "failed_calls": int(failed),
        }

    def get_recent_calls(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Retrieve recent safe operational call records.
        Does NOT return sensitive personal credentials or full transcripts.
        """
        query = """
        SELECT
            call_id,
            channel,
            language,
            started_at,
            ended_at,
            duration_seconds,
            outcome,
            success_reason,
            failure_reason,
            tool_used,
            escalation_created
        FROM calls
        ORDER BY id DESC
        LIMIT ?;
        """
        rows = self.db.execute_read(query, (limit,))
        results = []
        for r in rows:
            results.append(
                {
                    "call_id": r["call_id"],
                    "channel": r["channel"],
                    "language": r["language"],
                    "started_at": r["started_at"],
                    "ended_at": r["ended_at"],
                    "duration_seconds": r["duration_seconds"],
                    "outcome": r["outcome"],
                    "success_reason": r["success_reason"],
                    "failure_reason": r["failure_reason"],
                    "tool_used": r["tool_used"],
                    "escalation_created": bool(r["escalation_created"]),
                }
            )
        return results


# Singleton analytics service instance
_analytics_instance: AnalyticsService | None = None


def get_analytics_service(db: Database | None = None) -> AnalyticsService:
    """Get or create singleton AnalyticsService instance."""
    global _analytics_instance
    if db is not None:
        _analytics_instance = AnalyticsService(db)
    elif _analytics_instance is None:
        _analytics_instance = AnalyticsService()
    return _analytics_instance
