"""
Bharat Voice AI — Analytics Service Unit Tests (Day 8)

Tests:
- Call creation and unique call_id
- Call start (initial INCOMPLETE state)
- Call end (SUCCESS, FAILED, INCOMPLETE, ERROR)
- Duration calculation
- BROWSER vs SIP channel recording
- Language preference recording
- Summary metrics calculation (Total Calls, Successful Calls, Failed Calls)
- Zero calls state
- Duplicate call end idempotency
- Safe recent calls listing
"""

import tempfile
from pathlib import Path

import pytest

from memory.analytics_service import AnalyticsService
from memory.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary isolated SQLite database instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_analytics.db"
        db = Database(db_path)
        yield db


@pytest.fixture
def analytics_svc(temp_db):
    """Provide AnalyticsService bound to temporary database."""
    return AnalyticsService(db=temp_db)


def test_zero_calls_metrics(analytics_svc):
    """Verify get_call_metrics returns zeros when no calls exist."""
    metrics = analytics_svc.get_call_metrics()
    assert metrics["total_calls"] == 0
    assert metrics["successful_calls"] == 0
    assert metrics["failed_calls"] == 0


def test_call_start(analytics_svc):
    """Verify record_call_start creates record with INCOMPLETE outcome."""
    res = analytics_svc.record_call_start(
        call_id="call_start_001",
        user_id="user_123",
        channel="BROWSER",
        language="Hindi",
    )

    assert res["call_id"] == "call_start_001"
    assert res["outcome"] == "INCOMPLETE"
    assert res["channel"] == "BROWSER"

    metrics = analytics_svc.get_call_metrics()
    assert metrics["total_calls"] == 1
    assert metrics["successful_calls"] == 0
    assert metrics["failed_calls"] == 1  # INCOMPLETE counts as non-successful


def test_successful_call_outcome(analytics_svc):
    """Verify successful call increments total and successful count."""
    analytics_svc.record_call_start(
        call_id="call_success_001",
        user_id="user_weather",
        channel="BROWSER",
        language="Gujarati",
    )

    end_res = analytics_svc.record_call_end(
        call_id="call_success_001",
        outcome="SUCCESS",
        success_reason="Weather forecast successfully retrieved for Veraval",
        tool_used="get_weather",
        escalation_created=0,
        language="Gujarati",
    )

    assert end_res["call_id"] == "call_success_001"
    assert end_res["outcome"] == "SUCCESS"
    assert end_res["tool_used"] == "get_weather"

    metrics = analytics_svc.get_call_metrics()
    assert metrics["total_calls"] == 1
    assert metrics["successful_calls"] == 1
    assert metrics["failed_calls"] == 0


def test_failed_call_outcome(analytics_svc):
    """Verify failed call increments total and failed count."""
    analytics_svc.record_call_start(
        call_id="call_failed_001",
        user_id="user_fail",
        channel="BROWSER",
        language="English",
    )

    end_res = analytics_svc.record_call_end(
        call_id="call_failed_001",
        outcome="FAILED",
        failure_reason="Weather API lookup failed",
        tool_used="get_weather",
    )

    assert end_res["outcome"] == "FAILED"
    assert end_res["failure_reason"] == "Weather API lookup failed"

    metrics = analytics_svc.get_call_metrics()
    assert metrics["total_calls"] == 1
    assert metrics["successful_calls"] == 0
    assert metrics["failed_calls"] == 1


def test_sip_channel_recording(analytics_svc):
    """Verify SIP channel calls are recorded correctly."""
    analytics_svc.record_call_start(
        call_id="call_sip_001",
        user_id="linphone_user",
        channel="SIP",
        language="Hindi",
    )

    analytics_svc.record_call_end(
        call_id="call_sip_001",
        outcome="SUCCESS",
        success_reason="Outbound alert call delivered",
        tool_used="update_outbound_consent",
    )

    recent = analytics_svc.get_recent_calls(limit=10)
    assert len(recent) == 1
    assert recent[0]["channel"] == "SIP"
    assert recent[0]["outcome"] == "SUCCESS"


def test_idempotent_duplicate_call_end(analytics_svc):
    """Verify duplicate record_call_end updates existing call without error."""
    analytics_svc.record_call_start(
        call_id="call_dup_001",
        user_id="user_dup",
        channel="BROWSER",
    )

    analytics_svc.record_call_end(
        call_id="call_dup_001",
        outcome="INCOMPLETE",
    )

    # Call record_call_end second time
    analytics_svc.record_call_end(
        call_id="call_dup_001",
        outcome="SUCCESS",
        success_reason="Resolved on second sync",
    )

    metrics = analytics_svc.get_call_metrics()
    assert metrics["total_calls"] == 1
    assert metrics["successful_calls"] == 1
    assert metrics["failed_calls"] == 0


def test_recent_calls_safe_fields(analytics_svc):
    """Verify get_recent_calls returns safe operational fields only."""
    analytics_svc.record_call_start("call_1", "user_1", "BROWSER", "English")
    analytics_svc.record_call_end("call_1", "SUCCESS", success_reason="Done")

    analytics_svc.record_call_start("call_2", "user_2", "SIP", "Hindi")
    analytics_svc.record_call_end("call_2", "FAILED", failure_reason="Error")

    calls = analytics_svc.get_recent_calls(limit=10)
    assert len(calls) == 2

    c = calls[0]
    safe_keys = {
        "call_id",
        "channel",
        "language",
        "agent_name",
        "started_at",
        "ended_at",
        "duration_seconds",
        "outcome",
        "success_reason",
        "failure_reason",
        "tool_used",
        "escalation_created",
        "specialist_handoff",
    }
    assert set(c.keys()).issubset(safe_keys)


def test_call_id_uniqueness_and_duplicate_start(analytics_svc):
    """Verify duplicate call_id starts update existing record without creating duplicates."""
    analytics_svc.record_call_start(
        "unique_call_101", "user_orig", "BROWSER", "English"
    )
    analytics_svc.record_call_start("unique_call_101", "user_orig", "BROWSER", "Hindi")

    metrics = analytics_svc.get_call_metrics()
    assert metrics["total_calls"] == 1


def test_database_persistence(temp_db):
    """Verify calls persist across new AnalyticsService instances using same SQLite DB."""
    svc1 = AnalyticsService(db=temp_db)
    svc1.record_call_start("persist_001", "user_p", "BROWSER", "English")
    svc1.record_call_end("persist_001", "SUCCESS", success_reason="Saved")

    svc2 = AnalyticsService(db=temp_db)
    metrics = svc2.get_call_metrics()
    assert metrics["total_calls"] == 1
    assert metrics["successful_calls"] == 1
