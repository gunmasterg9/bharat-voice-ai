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
        agent_name: str = "bharat_voice_ai",
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
            call_id, user_id, channel, language, agent_name, started_at, outcome, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'INCOMPLETE', ?)
        ON CONFLICT(call_id) DO UPDATE SET
            user_id = excluded.user_id,
            channel = excluded.channel,
            agent_name = COALESCE(excluded.agent_name, calls.agent_name),
            language = COALESCE(excluded.language, calls.language);
        """
        params = (
            call_id,
            user_id,
            channel_clean,
            language,
            agent_name,
            now_iso,
            now_iso,
        )
        self.db.execute_write(query, params)

        logger.info(
            "[ANALYTICS] Call started | Call ID: %s | Channel: %s | User ID: %s | Agent: %s",
            call_id,
            channel_clean,
            user_id,
            agent_name,
        )
        return {
            "call_id": call_id,
            "user_id": user_id,
            "channel": channel_clean,
            "language": language,
            "agent_name": agent_name,
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
        agent_name: str | None = None,
        specialist_handoff: int = 0,
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
            "SELECT started_at, language, agent_name FROM calls WHERE call_id = ? LIMIT 1;",
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
                agent_name=agent_name or "bharat_voice_ai",
            )

        final_lang = language or (existing[0]["language"] if existing else None)
        final_agent = agent_name or (
            existing[0]["agent_name"] if existing else "bharat_voice_ai"
        )

        is_handoff = (
            1
            if (specialist_handoff or tool_used == "handoff_to_weather_specialist")
            else 0
        )

        update_query = """
        UPDATE calls
        SET ended_at = ?,
            duration_seconds = ?,
            outcome = ?,
            success_reason = ?,
            failure_reason = ?,
            tool_used = ?,
            escalation_created = ?,
            specialist_handoff = ?,
            agent_name = COALESCE(?, agent_name),
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
            is_handoff,
            final_agent,
            final_lang,
            call_id,
        )
        self.db.execute_write(update_query, params)

        logger.info(
            "[ANALYTICS] Call ended | Call ID: %s | Outcome: %s | Duration: %ds | Agent: %s | Handoff: %d",
            call_id,
            outcome_clean,
            duration_seconds,
            final_agent,
            is_handoff,
        )
        return {
            "call_id": call_id,
            "outcome": outcome_clean,
            "duration_seconds": duration_seconds,
            "success_reason": success_reason,
            "failure_reason": failure_reason,
            "tool_used": tool_used,
            "escalation_created": 1 if escalation_created else 0,
            "specialist_handoff": is_handoff,
            "agent_name": final_agent,
        }

    def get_call_metrics(self) -> dict[str, int]:
        """
        Get aggregated call analytics summary.
        Calculates:
        - total_calls = COUNT(*)
        - successful_calls = COUNT(outcome = 'SUCCESS')
        - failed_calls = COUNT(outcome != 'SUCCESS')
        - specialist_handoffs = SUM(specialist_handoff)
        """
        query = """
        SELECT
            COUNT(*) as total_calls,
            SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) as successful_calls,
            SUM(CASE WHEN outcome != 'SUCCESS' THEN 1 ELSE 0 END) as failed_calls,
            SUM(CASE WHEN specialist_handoff = 1 OR tool_used = 'handoff_to_weather_specialist' THEN 1 ELSE 0 END) as specialist_handoffs
        FROM calls;
        """
        rows = self.db.execute_read(query)
        if not rows or rows[0]["total_calls"] is None:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "specialist_handoffs": 0,
            }

        total = rows[0]["total_calls"] or 0
        success = rows[0]["successful_calls"] or 0
        failed = rows[0]["failed_calls"] or 0
        handoffs = rows[0]["specialist_handoffs"] or 0

        return {
            "total_calls": int(total),
            "successful_calls": int(success),
            "failed_calls": int(failed),
            "specialist_handoffs": int(handoffs),
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
            agent_name,
            started_at,
            ended_at,
            duration_seconds,
            outcome,
            success_reason,
            failure_reason,
            tool_used,
            escalation_created,
            specialist_handoff
        FROM calls
        ORDER BY id DESC
        LIMIT ?;
        """
        rows = self.db.execute_read(query, (limit,))
        results = []
        for r in rows:
            r_dict = dict(r)
            results.append(
                {
                    "call_id": r_dict.get("call_id"),
                    "channel": r_dict.get("channel"),
                    "language": r_dict.get("language"),
                    "agent_name": r_dict.get("agent_name") or "bharat_voice_ai",
                    "started_at": r_dict.get("started_at"),
                    "ended_at": r_dict.get("ended_at"),
                    "duration_seconds": r_dict.get("duration_seconds"),
                    "outcome": r_dict.get("outcome"),
                    "success_reason": r_dict.get("success_reason"),
                    "failure_reason": r_dict.get("failure_reason"),
                    "tool_used": r_dict.get("tool_used"),
                    "escalation_created": bool(r_dict.get("escalation_created", 0)),
                    "specialist_handoff": bool(r_dict.get("specialist_handoff", 0)),
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
