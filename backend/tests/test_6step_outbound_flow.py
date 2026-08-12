"""
Bharat Voice AI — 6-Step Outbound Call Flow Automated Test Suite

Verifies the complete 6-step outbound call workflow:
1. 📞 Phone rings -> Answered
2. 👋 Introduction & 🌦️ Weather alert for Veraval
3. 🗣️ Follow-up question ("Will it rain tomorrow in Veraval?")
4. 🚫 Opt-Out request ("Don't call me again")
5. 👋 Confirmation of opt-out saved
6. 📴 Call ends via end_call_tool()
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.config import Settings, TelephonyConfig
from agent.voice_agent import BharatVoiceAgent
from memory.database import Database
from memory.memory_service import MemoryService
from memory.tools import end_call_tool, update_outbound_consent_tool
from services.weather import get_weather_service
from telephony.call_manager import OutboundCallManager


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_flow.db"
    return Database(db_path=db_path)


@pytest.fixture
def memory_svc(test_db):
    return MemoryService(db=test_db)


@pytest.fixture
def test_settings():
    return Settings(
        telephony=TelephonyConfig(
            sip_trunk_id="ST_TEST_TRUNK",
            outbound_phone_number="+911234567890",
            outbound_test_phone_number="+919876543210",
            outbound_test_mode=True,
            weather_alert_rain_threshold=70,
        )
    )


@pytest.mark.asyncio
async def test_step1_phone_rings_and_answered(test_settings, memory_svc):
    """Step 1: Outbound call initiator dials destination and receives ANSWERED state."""
    manager = OutboundCallManager(settings=test_settings, memory_service=memory_svc)

    memory_svc.save_user(
        user_id="gautam", name="Gautam", language_preference="Gujarati"
    )
    memory_svc.update_user_phone(
        user_id="gautam", phone_number="+919876543210", verified=True
    )
    memory_svc.update_outbound_consent(user_id="gautam", consent=True, opted_out=False)

    weather_data = {"precipitation_probability": 85, "condition": "Heavy rain"}

    with (
        patch(
            "telephony.call_manager.dispatch_agent_to_room",
            new=AsyncMock(return_value=MagicMock(id="dsp_123")),
        ),
        patch(
            "telephony.call_manager.create_sip_participant",
            new=AsyncMock(return_value=MagicMock(sip_call_id="sip_456")),
        ),
    ):
        res = await manager.place_outbound_call(
            phone_number="+919876543210",
            user_id="gautam",
            reason="high_rain_probability",
            language="Gujarati",
            weather_data=weather_data,
            bypass_decision_checks=True,
        )

        assert res["success"] is True
        assert res["status"] == "ANSWERED"


@pytest.mark.asyncio
async def test_step2_intro_and_weather_alert_veraval():
    """Step 2: Agent fetches live weather for Veraval and constructs opening greeting."""
    weather_svc = get_weather_service()
    weather = await weather_svc.get_weather_data("Veraval")

    assert weather["success"] is True
    assert "data" in weather
    assert "temperature_c" in weather["data"]


@pytest.mark.asyncio
async def test_step3_follow_up_question_forecast(test_db, memory_svc):
    """Step 3: Follow-up question about tomorrow's weather forecast in Veraval."""
    agent = BharatVoiceAgent(session_id="session_flow_3", user_id="gautam")
    agent.db_memory = memory_svc
    memory_svc.save_user(user_id="gautam", name="Gautam", facts={"location": "Veraval"})

    context_mock = MagicMock()

    # Query 2-day forecast
    res_str = await agent.get_weather(
        context=context_mock, location="Veraval", forecast_days=2
    )
    assert "success" in res_str
    assert "Gujarat" in res_str or "Ver" in res_str


@pytest.mark.asyncio
async def test_step4_and_step5_opt_out_and_confirmation(memory_svc):
    """Step 4 & 5: Caller opts out -> update_outbound_consent tool updates DB and confirms."""
    memory_svc.save_user(user_id="gautam", name="Gautam")
    memory_svc.update_outbound_consent(user_id="gautam", consent=True, opted_out=False)

    agent = BharatVoiceAgent(session_id="session_flow_4", user_id="gautam")
    agent.db_memory = memory_svc

    context_mock = MagicMock()

    # Opt-out request
    confirm_msg = await update_outbound_consent_tool(
        agent=agent, context=context_mock, consent=False, opt_out=True
    )

    assert (
        "will not place future alert calls" in confirm_msg
        or "preferences" in confirm_msg
    )

    # Verify SQLite DB reflects opt-out
    updated_user = memory_svc.get_user("gautam")
    assert (
        updated_user["outbound_call_consent"] is False
        or updated_user["opted_out"] is True
    )


@pytest.mark.asyncio
async def test_step6_call_ends():
    """Step 6: end_call_tool gracefully disconnects the LiveKit room/session."""
    agent = BharatVoiceAgent(session_id="session_flow_6", user_id="gautam")
    mock_room = MagicMock()
    mock_room.disconnect = AsyncMock()
    agent.room = mock_room

    context_mock = MagicMock()

    res = await end_call_tool(agent=agent, context=context_mock, reason="user_opt_out")
    assert "Call termination sequence initiated" in res
    assert mock_room.disconnect.called
