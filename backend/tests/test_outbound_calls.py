"""
Bharat Voice AI — Day 6 Outbound Call Unit & Integration Tests
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.config import Settings, TelephonyConfig
from memory.database import Database
from memory.memory_service import MemoryService, mask_phone_number
from services.weather_alert_service import WeatherAlertService, validate_e164_phone
from telephony.call_manager import OutboundCallManager


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_outbound.db"
    db = Database(db_path=db_path)
    return db


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
            outbound_call_start_hour=8,
            outbound_call_end_hour=20,
        )
    )


def test_e164_phone_validation():
    valid, res = validate_e164_phone("+919876543210")
    assert valid is True
    assert res == "+919876543210"

    valid_us, _ = validate_e164_phone("+14155552671")
    assert valid_us is True

    invalid_format, _ = validate_e164_phone("9876543210")
    assert invalid_format is False

    invalid_empty, _ = validate_e164_phone("")
    assert invalid_empty is False


def test_phone_number_masking():
    masked = mask_phone_number("+919876543210")
    assert masked.startswith("+91")
    assert masked.endswith("3210")
    assert "*" in masked
    assert "98765" not in masked


def test_outbound_consent_and_opt_out_updates(memory_svc):
    user = memory_svc.save_user(user_id="user_test_1", name="Gautam")
    assert user["outbound_call_consent"] is False
    assert user["opted_out"] is False

    # Grant consent
    updated = memory_svc.update_outbound_consent(
        user_id="user_test_1", consent=True, opted_out=False
    )
    assert updated["outbound_call_consent"] is True
    assert updated["opted_out"] is False

    # Opt out
    opt_out = memory_svc.update_outbound_consent(
        user_id="user_test_1", consent=False, opted_out=True
    )
    assert opt_out["outbound_call_consent"] is False
    assert opt_out["opted_out"] is True


def test_weather_alert_decision_logic(test_settings, memory_svc):
    alert_svc = WeatherAlertService(settings=test_settings, memory_service=memory_svc)

    memory_svc.save_user(user_id="gautam", name="Gautam")
    memory_svc.update_user_phone(
        user_id="gautam", phone_number="+919876543210", verified=True
    )
    memory_svc.update_outbound_consent(user_id="gautam", consent=True, opted_out=False)
    profile = memory_svc.get_user("gautam")

    # 1. Weather below threshold
    weather_low = {"precipitation_probability": 40, "condition": "Partly cloudy"}
    should_call, reason = alert_svc.should_call_user(
        weather_low, profile, current_dt=datetime(2026, 8, 11, 10, 0)
    )
    assert should_call is False
    assert "weather_below_threshold" in reason

    # 2. Weather above threshold
    weather_high = {"precipitation_probability": 80, "condition": "Moderate rain"}
    should_call, reason = alert_svc.should_call_user(
        weather_high, profile, current_dt=datetime(2026, 8, 11, 10, 0)
    )
    assert should_call is True
    assert "high_rain_probability" in reason

    # 3. Severe weather condition (thunderstorm)
    weather_severe = {"precipitation_probability": 50, "condition": "Thunderstorm"}
    should_call_severe, reason_severe = alert_svc.should_call_user(
        weather_severe, profile, current_dt=datetime(2026, 8, 11, 10, 0)
    )
    assert should_call_severe is True
    assert "severe_weather_alert" in reason_severe

    # 4. Outside calling hours (e.g. 23:00)
    should_call_night, reason_night = alert_svc.should_call_user(
        weather_high, profile, current_dt=datetime(2026, 8, 11, 23, 0)
    )
    assert should_call_night is False
    assert "outside_calling_hours" in reason_night

    # 5. User opted out
    memory_svc.update_outbound_consent(user_id="gautam", consent=False, opted_out=True)
    profile_opted_out = memory_svc.get_user("gautam")
    should_call_opt, reason_opt = alert_svc.should_call_user(
        weather_high, profile_opted_out, current_dt=datetime(2026, 8, 11, 10, 0)
    )
    assert should_call_opt is False
    assert reason_opt == "user_opted_out"


@pytest.mark.asyncio
async def test_outbound_call_manager_orchestration(test_settings, memory_svc):
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
        ) as mock_dispatch,
        patch(
            "telephony.call_manager.create_sip_participant",
            new=AsyncMock(return_value=MagicMock(sip_call_id="sip_456")),
        ) as mock_sip,
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
        assert mock_dispatch.called
        assert mock_sip.called

        user_profile = memory_svc.get_user("gautam")
        assert user_profile["last_outbound_reason"] == "high_rain_probability"
