"""
Bharat Voice AI — Day 6 Outbound Linphone Unit Tests
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.config import LiveKitConfig, Settings, TelephonyConfig
from memory.database import Database
from memory.memory_service import MemoryService
from telephony.outbound.dial import dial_linphone
from telephony.outbound.sip import create_sip_participant, dispatch_agent_to_room


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_linphone.db"
    return Database(db_path=db_path)


@pytest.fixture
def memory_svc(test_db):
    return MemoryService(db=test_db)


@pytest.fixture
def test_settings():
    return Settings(
        livekit=LiveKitConfig(
            url="wss://test.livekit.cloud",
            api_key="test_api_key",
            api_secret="test_api_secret",
        ),
        telephony=TelephonyConfig(
            sip_trunk_id="ST_B4bMBK9TtaqH",
            linphone_username="gautammax",
            linphone_domain="sip.linphone.org",
            linphone_sip_uri="sip:gautammax@sip.linphone.org",
            outbound_test_mode=True,
        ),
    )


def test_linphone_environment_config(test_settings):
    assert test_settings.telephony.sip_trunk_id == "ST_B4bMBK9TtaqH"
    assert test_settings.telephony.linphone_username == "gautammax"
    assert test_settings.telephony.linphone_domain == "sip.linphone.org"
    assert test_settings.telephony.linphone_sip_uri == "sip:gautammax@sip.linphone.org"


def test_outbound_consent_validation(memory_svc):
    memory_svc.save_user(user_id="gautammax", name="Gautam")
    memory_svc.update_outbound_consent(
        user_id="gautammax", consent=True, opted_out=False
    )


    profile = memory_svc.get_user("gautammax")
    assert profile["outbound_call_consent"] is True

    # User revokes consent
    revoked = memory_svc.update_outbound_consent(
        user_id="gautammax", consent=False, opted_out=True
    )
    assert revoked["outbound_call_consent"] is False
    assert revoked["opted_out"] is True


@pytest.mark.asyncio
async def test_outbound_dispatch_mocking(test_settings):
    with patch("livekit.api.LiveKitAPI") as mock_lk:
        mock_client = AsyncMock()
        mock_lk.return_value = mock_client
        mock_client.agent_dispatch.create_dispatch = AsyncMock(
            return_value=MagicMock(id="dsp_12345")
        )

        res = await dispatch_agent_to_room(
            room_name="test-room-123",
            metadata={"call_type": "outbound_weather_alert"},
            settings=test_settings,
        )

        assert res.id == "dsp_12345"
        mock_client.agent_dispatch.create_dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_create_sip_participant_mocking(test_settings):
    with patch("livekit.api.LiveKitAPI") as mock_lk:
        mock_client = AsyncMock()
        mock_lk.return_value = mock_client
        mock_client.sip.create_sip_participant = AsyncMock(
            return_value=MagicMock(sip_call_id="sip_call_98765")
        )

        sip_info = await create_sip_participant(
            room_name="test-room-123",
            phone_number="sip:gautammax@sip.linphone.org",
            participant_identity="gautammax",
            participant_name="Gautam",
            settings=test_settings,
        )

        assert sip_info.sip_call_id == "sip_call_98765"
        mock_client.sip.create_sip_participant.assert_called_once()


@pytest.mark.asyncio
async def test_dial_linphone_success_flow(test_settings, memory_svc):
    with (
        patch("telephony.outbound.dial.load_settings", return_value=test_settings),
        patch("telephony.outbound.dial.get_memory_service", return_value=memory_svc),
        patch(
            "telephony.outbound.dial.dispatch_agent_to_room",
            new=AsyncMock(return_value=MagicMock(id="dsp_test")),
        ) as mock_dispatch,
        patch(
            "telephony.outbound.dial.create_sip_participant",
            new=AsyncMock(return_value=MagicMock(sip_call_id="sip_test")),
        ) as mock_sip,
    ):
        await dial_linphone(to_user="gautammax")

        assert mock_dispatch.called
        assert mock_sip.called
        assert mock_sip.call_args[1]["phone_number"] == "gautammax"

