"""
Bharat Voice AI — Day 9 Specialist Agent & Multi-Agent Handoff Tests

Comprehensive unit tests and LLM evaluation tests for Day 9 requirements:
- Main agent vs Specialist agent responsibilities
- Automatic handoff for detailed weather requests
- Main agent announcement before handoff
- Specialist introduction and direct execution without re-asking
- Language preservation across handoff (English, Hindi Devanagari, Gujarati script, Hinglish)
- Real Open-Meteo weather tool execution
- Handoff failure & Weather API failure graceful fallbacks
- Non-weather queries & Human escalation staying with main agent
- Day 8/9 call analytics and SQLite persistence across restart
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from agent.guardrails import guardrail_engine
from agent.specialist import BharatWeatherSpecialist
from agent.voice_agent import BharatVoiceAgent
from memory.analytics_service import AnalyticsService
from memory.database import Database, reset_db_singleton
from memory.memory_service import MemoryService



def _get_handoff_text(res) -> str:
    if isinstance(res, tuple):
        spec, ann = res
        intro = spec.get_introduction_message(spec.active_language) if hasattr(spec, "get_introduction_message") else ""
        return f"{ann}\n{intro}"
    return str(res)


# ---------------------------------------------------------------------------
# Test 1: Normal Main Agent (Greeting -> Main Agent, No Handoff)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_normal_main_agent(tmp_path) -> None:
    """Main Agent handles standard greetings without triggering specialist handoff."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    agent = BharatVoiceAgent(
        session_id="session_test_1", user_id="user_1", db_memory=mem
    )

    # Process user turn
    turn_res = await agent.process_user_turn("Hello")
    assert turn_res == "Hello"
    assert agent.tool_used != "handoff_to_weather_specialist"
    assert not hasattr(agent, "active_specialist") or agent.active_specialist is None


# ---------------------------------------------------------------------------
# Test 2: General Question (Identity -> Main Agent, No Handoff)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_general_question(tmp_path) -> None:
    """General identity questions are answered by Main Agent without handoff."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    agent = BharatVoiceAgent(
        session_id="session_test_2", user_id="user_2", db_memory=mem
    )

    turn_res = await agent.process_user_turn("Who are you?")
    assert turn_res == "Who are you?"
    assert agent.tool_used != "handoff_to_weather_specialist"


# ---------------------------------------------------------------------------
# Test 3: Weather Handoff (Weather Request -> Announcement + Handoff + Specialist Execution)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_weather_handoff(tmp_path) -> None:
    """Weather queries trigger handoff_to_weather_specialist, announcement, and real get_weather execution."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    agent = BharatVoiceAgent(
        session_id="session_test_3", user_id="user_3", db_memory=mem
    )

    # Mock RunContext
    mock_ctx = AsyncMock()
    mock_ctx.session = AsyncMock()

    handoff_output_raw = await agent.handoff_to_weather_specialist(
        context=mock_ctx,
        location="Veraval",
        original_request="What is the weather in Veraval today?",
        language="English",
    )
    handoff_output = _get_handoff_text(handoff_output_raw)

    # Verify announcement and introduction
    assert "weather specialist" in handoff_output.lower()
    assert "Bharat Weather Specialist" in handoff_output
    assert agent.tool_used == "handoff_to_weather_specialist"

    # Verify specialist creation and real get_weather call
    specialist = getattr(agent, "active_specialist", None)
    assert specialist is not None
    assert isinstance(specialist, BharatWeatherSpecialist)

    # Execute specialist get_weather tool
    weather_res_raw = await specialist.get_weather(context=mock_ctx, location="Veraval")
    weather_res = json.loads(weather_res_raw)

    assert weather_res.get("success") is True
    assert (
        "veraval" in weather_res["data"]["location"].lower()
        or "verāval" in weather_res["data"]["location"].lower()
    )
    assert "temperature_c" in weather_res["data"]


# ---------------------------------------------------------------------------
# Test 4: Weather Follow-Up (Handled by Specialist directly)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_weather_followup(tmp_path) -> None:
    """Specialist continues handling weather follow-up questions without unnecessary hand-back."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    specialist = BharatWeatherSpecialist(
        session_id="session_test_4",
        user_id="user_4",
        active_language="English",
        location="Veraval",
        db_memory=mem,
    )

    mock_ctx = AsyncMock()
    # User asks follow-up about humidity
    res_raw = await specialist.get_weather(context=mock_ctx, location="Veraval")
    res = json.loads(res_raw)

    assert res["success"] is True
    assert "humidity_percent" in res["data"]
    assert specialist.task_completed is True


# ---------------------------------------------------------------------------
# Test 5: Language Handoff (Hindi Devanagari Script)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_hindi_handoff(tmp_path) -> None:
    """Hindi weather request triggers Hindi announcement and Hindi specialist intro in Devanagari script."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    agent = BharatVoiceAgent(
        session_id="session_test_5", user_id="user_5", db_memory=mem
    )
    agent.set_active_language("Hindi", update_db=True)

    mock_ctx = AsyncMock()
    mock_ctx.session = AsyncMock()

    handoff_output_raw = await agent.handoff_to_weather_specialist(
        context=mock_ctx,
        location="Veraval",
        original_request="आज वेरावल में मौसम कैसा है?",
        language="Hindi",
    )
    handoff_output = _get_handoff_text(handoff_output_raw)

    assert "मौसम विशेषज्ञ" in handoff_output
    assert "नमस्ते" in handoff_output

    specialist = agent.active_specialist
    intro = specialist.get_introduction_message("Hindi")
    assert "मौसम विशेषज्ञ" in intro


# ---------------------------------------------------------------------------
# Test 6: Gujarati Handoff (Gujarati Script)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gujarati_handoff(tmp_path) -> None:
    """Gujarati weather request triggers Gujarati announcement and Gujarati script intro."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    agent = BharatVoiceAgent(
        session_id="session_test_6", user_id="user_6", db_memory=mem
    )
    agent.set_active_language("Gujarati", update_db=True)

    mock_ctx = AsyncMock()
    mock_ctx.session = AsyncMock()

    handoff_output_raw = await agent.handoff_to_weather_specialist(
        context=mock_ctx,
        location="Veraval",
        original_request="આજે વેરાવળમાં હવામાન કેવું છે?",
        language="Gujarati",
    )
    handoff_output = _get_handoff_text(handoff_output_raw)

    assert "હવામાન નિષ્ણાત" in handoff_output
    assert "નમસ્તે" in handoff_output


# ---------------------------------------------------------------------------
# Test 7: Code-Mixed Language (Hinglish/Gujlish)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_code_mixed(tmp_path) -> None:
    """Code-mixed queries ('Veraval mein aaj weather kaisa hai?') are processed correctly."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    agent = BharatVoiceAgent(
        session_id="session_test_7", user_id="user_7", db_memory=mem
    )
    agent.set_active_language("Hinglish", update_db=False)

    mock_ctx = AsyncMock()
    mock_ctx.session = AsyncMock()

    handoff_output_raw = await agent.handoff_to_weather_specialist(
        context=mock_ctx,
        location="Veraval",
        original_request="Veraval mein aaj weather kaisa hai?",
        language="Hinglish",
    )
    handoff_output = _get_handoff_text(handoff_output_raw)

    assert (
        "weather specialist" in handoff_output.lower()
        or "मौसम विशेषज्ञ" in handoff_output
    )
    specialist = agent.active_specialist
    assert specialist is not None


# ---------------------------------------------------------------------------
# Test 8: Non-Weather Routing ("What can you do?" -> Main Agent)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_non_weather(tmp_path) -> None:
    """General capability questions stay with Main Agent, no handoff."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    agent = BharatVoiceAgent(
        session_id="session_test_8", user_id="user_8", db_memory=mem
    )

    res = await agent.process_user_turn("What can you do?")
    assert res == "What can you do?"
    assert agent.tool_used != "handoff_to_weather_specialist"


# ---------------------------------------------------------------------------
# Test 9: Human Help Routing ("I want to talk to a human")
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_human_help(tmp_path) -> None:
    """Human assistance requests trigger Day 7 escalation flow in Main Agent, NOT weather specialist."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    agent = BharatVoiceAgent(
        session_id="session_test_9", user_id="user_9", db_memory=mem
    )

    await agent.process_user_turn("I want to talk to a human.")

    # State machine enters WAITING_FOR_PERMISSION
    assert agent.escalation_state == "WAITING_FOR_PERMISSION"
    assert agent.tool_used != "handoff_to_weather_specialist"


# ---------------------------------------------------------------------------
# Test 10: Handoff Failure (Graceful Fallback)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handoff_failure(tmp_path) -> None:
    """Simulated specialist creation/session update failure falls back gracefully without crash."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    agent = BharatVoiceAgent(
        session_id="session_test_10", user_id="user_10", db_memory=mem
    )

    mock_ctx = AsyncMock()
    # Simulate exception during update_agent
    mock_ctx.session.update_agent.side_effect = Exception(
        "LiveKit Session Disconnected"
    )

    # Call handoff with patch forcing exception in specialist creation
    with patch(
        "agent.specialist.BharatWeatherSpecialist",
        side_effect=Exception("Initialization failed"),
    ):
        res = await agent.handoff_to_weather_specialist(
            context=mock_ctx,
            location="Veraval",
            original_request="Weather in Veraval",
        )

    assert "unable to connect you to the weather specialist" in _get_handoff_text(res).lower()


# ---------------------------------------------------------------------------
# Test 11: Weather API Failure (Graceful Explanation, No Hallucination)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_weather_api_failure(tmp_path) -> None:
    """Weather API failure is reported gracefully by specialist without hallucinated values."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    specialist = BharatWeatherSpecialist(
        session_id="session_test_11",
        user_id="user_11",
        db_memory=mem,
    )

    mock_ctx = AsyncMock()
    mock_weather_svc = AsyncMock()
    mock_weather_svc.get_weather_data.return_value = {
        "success": False,
        "error": "weather_service_unavailable",
        "message": "Live weather service is currently unavailable.",
    }

    with patch("agent.specialist.get_weather_service", return_value=mock_weather_svc):
        raw_res = await specialist.get_weather(context=mock_ctx, location="Veraval")
        res = json.loads(raw_res)

        assert res["success"] is False
        assert specialist.task_failed is True


# ---------------------------------------------------------------------------
# Test 12: Analytics Recording (Main Agent vs Specialist)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_analytics_recording(tmp_path) -> None:
    """Analytics Service records both normal calls and specialist handoff calls correctly."""
    reset_db_singleton()
    db = Database(db_path=tmp_path / "test_bharat.db")
    analytics = AnalyticsService(db=db)

    # Record Call 1: Normal call
    analytics.record_call_start(
        call_id="call_normal_1",
        user_id="u1",
        channel="BROWSER",
        agent_name="bharat_voice_ai",
    )
    analytics.record_call_end(
        call_id="call_normal_1",
        outcome="SUCCESS",
        tool_used="lookup_caller",
        agent_name="bharat_voice_ai",
    )

    # Record Call 2: Specialist handoff call
    analytics.record_call_start(
        call_id="call_specialist_1",
        user_id="u2",
        channel="BROWSER",
        agent_name="weather_specialist",
    )
    analytics.record_call_end(
        call_id="call_specialist_1",
        outcome="SUCCESS",
        tool_used="handoff_to_weather_specialist",
        specialist_handoff=1,
        agent_name="weather_specialist",
    )

    metrics = analytics.get_call_metrics()
    assert metrics["total_calls"] == 2
    assert metrics["successful_calls"] == 2
    assert metrics["specialist_handoffs"] == 1

    recent = analytics.get_recent_calls(limit=10)
    assert len(recent) == 2
    assert recent[0]["specialist_handoff"] is True


# ---------------------------------------------------------------------------
# Test 13: Memory & Language Retention
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_memory_and_language_retention(tmp_path) -> None:
    """Saved caller profile language preference is respected by weather specialist."""
    db = Database(db_path=tmp_path / "test_bharat.db")
    mem = MemoryService(db)
    # Save Hindi preference in profile
    mem.save_user(
        user_id="caller_hindi",
        name="Ramesh",
        language_preference="Hindi",
        facts={"location": "Veraval"},
    )

    # Main Agent load profile
    agent = BharatVoiceAgent(session_id="s13", user_id="caller_hindi", db_memory=mem)
    assert agent.active_language == "Hindi"

    mock_ctx = AsyncMock()
    mock_ctx.session = AsyncMock()

    await agent.handoff_to_weather_specialist(
        context=mock_ctx,
        original_request="मौसम कैसा है?",
    )

    specialist = agent.active_specialist
    assert specialist.active_language == "Hindi"
    intro = specialist.get_introduction_message()
    assert "नमस्ते" in intro


# ---------------------------------------------------------------------------
# Test 14: System Restart Persistence
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_system_restart(tmp_path) -> None:
    """Simulated application restart maintains DB schema and agent functionality."""
    db_path = tmp_path / "restart_test.db"

    # Step 1: Save data before restart
    db1 = Database(db_path=db_path)
    analytics1 = AnalyticsService(db=db1)
    analytics1.record_call_start("restart_call_1", "user_r", "BROWSER")
    analytics1.record_call_end(
        "restart_call_1",
        "SUCCESS",
        tool_used="handoff_to_weather_specialist",
        specialist_handoff=1,
    )

    # Step 2: Re-initialize DB (simulating process restart)
    reset_db_singleton()
    db2 = Database(db_path=db_path)
    analytics2 = AnalyticsService(db=db2)

    metrics = analytics2.get_call_metrics()
    assert metrics["total_calls"] == 1
    assert metrics["specialist_handoffs"] == 1

    # Verify agent instantiation after restart
    mem2 = MemoryService(db2)
    agent = BharatVoiceAgent(
        session_id="restart_session", user_id="user_r", db_memory=mem2
    )
    assert agent.instructions is not None


# ---------------------------------------------------------------------------
# Test 15: Acceptance Suite for Prompt Requirements (10 Test Cases)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_user_request_10_scenarios(tmp_path) -> None:
    """Verify all 10 prompt test cases for Day 9 Weather Specialist Handoff."""
    db = Database(db_path=tmp_path / "acceptance_test.db")
    mem = MemoryService(db)
    mock_ctx = AsyncMock()
    mock_ctx.session = AsyncMock()

    # TEST 1: Weather query -> Handoff -> get_weather -> No JSON output
    agent1 = BharatVoiceAgent(session_id="s_acc_1", user_id="u_acc_1", db_memory=mem)
    h_out1 = _get_handoff_text(
        await agent1.handoff_to_weather_specialist(
            context=mock_ctx,
            location="Veraval",
            original_request="What is the weather today in Veraval?",
            language="English",
        )
    )
    assert "weather specialist" in h_out1.lower()
    sp1 = agent1.active_specialist
    w_raw1 = await sp1.get_weather(context=mock_ctx, location="Veraval", forecast_days=1)
    w_data1 = json.loads(w_raw1)
    assert w_data1["success"] is True
    loc1 = w_data1["data"]["location"].lower()
    assert "veraval" in loc1 or "verāval" in loc1
    # Guardrail check on assistant turn prevents JSON leakage
    assert guardrail_engine.filter_output_claims("This JSON response is for a function call...") == ""

    # TEST 2: Continuation with "Okay"
    assert sp1.initial_request == "What is the weather today in Veraval?"
    assert sp1.location == "Veraval"

    # TEST 3: Temperature query
    w_raw3 = await sp1.get_weather(context=mock_ctx, location="Veraval", forecast_days=1)
    w_data3 = json.loads(w_raw3)
    assert "temperature_c" in w_data3["data"]

    # TEST 4: Hindi query
    agent4 = BharatVoiceAgent(session_id="s_acc_4", user_id="u_acc_4", db_memory=mem)
    agent4.set_active_language("Hindi", update_db=False)
    h_out4 = _get_handoff_text(
        await agent4.handoff_to_weather_specialist(
            context=mock_ctx,
            location="Veraval",
            original_request="आज वेरावल में मौसम कैसा है?",
            language="Hindi",
        )
    )
    assert "मौसम विशेषज्ञ" in h_out4

    # TEST 5: Gujarati query
    agent5 = BharatVoiceAgent(session_id="s_acc_5", user_id="u_acc_5", db_memory=mem)
    agent5.set_active_language("Gujarati", update_db=False)
    h_out5 = _get_handoff_text(
        await agent5.handoff_to_weather_specialist(
            context=mock_ctx,
            location="Veraval",
            original_request="આજે વેરાવળમાં હવામાન કેવું છે?",
            language="Gujarati",
        )
    )
    assert "હવામાન નિષ્ણાત" in h_out5

    # TEST 6: Location Ahmedabad (Not Veraval)
    w_raw6 = await sp1.get_weather(context=mock_ctx, location="Ahmedabad", forecast_days=1)
    w_data6 = json.loads(w_raw6)
    assert "ahmedabad" in w_data6["data"]["location"].lower()

    # TEST 7: Speech normalization Vedawal -> Veraval
    w_raw7 = await sp1.get_weather(context=mock_ctx, location="Vedawal", forecast_days=1)
    w_data7 = json.loads(w_raw7)
    loc7 = w_data7["data"]["location"].lower()
    assert "veraval" in loc7 or "verāval" in loc7

    # TEST 8: Weather API Failure
    mock_weather_svc = AsyncMock()
    mock_weather_svc.get_weather_data.return_value = {
        "success": False,
        "error": "weather_service_unavailable",
        "message": "Live weather service is currently unavailable.",
    }
    with patch("agent.specialist.get_weather_service", return_value=mock_weather_svc):
        w_raw8 = await sp1.get_weather(context=mock_ctx, location="Veraval")
        w_data8 = json.loads(w_raw8)
        assert w_data8["success"] is False
        assert sp1.task_failed is True

    # TEST 9: Normal question "Who are you?" -> Main agent, no handoff
    agent9 = BharatVoiceAgent(session_id="s_acc_9", user_id="u_acc_9", db_memory=mem)
    turn_res9 = await agent9.process_user_turn("Who are you?")
    assert turn_res9 == "Who are you?"
    assert agent9.tool_used != "handoff_to_weather_specialist"

    # TEST 10: Human help "I want to talk to a human." -> Escalation workflow, no specialist
    agent10 = BharatVoiceAgent(session_id="s_acc_10", user_id="u_acc_10", db_memory=mem)
    turn_res10 = await agent10.process_user_turn("I want to talk to a human.")
    assert turn_res10 == "I want to talk to a human."
    assert agent10.tool_used != "handoff_to_weather_specialist"

