"""
Bharat Voice AI — Telephony Outbound SIP Module

Handles direct interaction with LiveKit Server API to:
1. Dispatch the agent process to a targeted room (`create_dispatch`).
2. Dial an outbound phone participant via SIP (`create_sip_participant`).
"""

import json
from typing import Any

from livekit import api as lk_api

from agent.config import Settings, load_settings
from agent.logger import COMPONENT_AGENT, get_logger

logger = get_logger(COMPONENT_AGENT)


async def dispatch_agent_to_room(
    room_name: str,
    metadata: dict[str, Any],
    settings: Settings | None = None,
) -> Any:
    """
    Dispatch the Bharat Voice AI agent to a specific LiveKit room using AgentDispatch service.

    Args:
        room_name: Target LiveKit room name.
        metadata: Dictionary containing call context (call_type, user_id, reason, language, etc.).
        settings: Optional system Settings object.

    Returns:
        AgentDispatch object returned by LiveKit server API.
    """
    cfg = settings or load_settings()
    lk_client = lk_api.LiveKitAPI(
        url=cfg.livekit.url,
        api_key=cfg.livekit.api_key,
        api_secret=cfg.livekit.api_secret,
    )

    try:
        metadata_str = json.dumps(metadata, ensure_ascii=False)
        dispatch_req = lk_api.CreateAgentDispatchRequest(
            agent_name=cfg.agent_name,
            room=room_name,
            metadata=metadata_str,
        )

        logger.info(
            "[TELEPHONY] Dispatching agent '%s' to room '%s'...",
            cfg.agent_name,
            room_name,
        )
        dispatch_res = await lk_client.agent_dispatch.create_dispatch(dispatch_req)
        logger.info(
            "[TELEPHONY] Agent dispatched successfully! Dispatch ID: %s",
            getattr(dispatch_res, "id", "created"),
        )
        return dispatch_res
    finally:
        await lk_client.aclose()


async def create_sip_participant(
    room_name: str,
    phone_number: str,
    participant_identity: str,
    participant_name: str = "Outbound Callee",
    metadata: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> Any:
    """
    Initiate an outbound SIP call connecting a phone participant to a LiveKit room.

    Args:
        room_name: Unique LiveKit room name.
        phone_number: Destination phone number or SIP URI (e.g. sip:gautammax@sip.linphone.org or gautammax).
        participant_identity: Identity string for the remote participant.
        participant_name: Display name for participant.
        metadata: Optional metadata dictionary.
        settings: Optional system Settings object.

    Returns:
        SIPParticipantInfo object returned by LiveKit server API.
    """
    cfg = settings or load_settings()
    trunk_id = cfg.telephony.sip_trunk_id

    if not trunk_id:
        logger.error(
            "[TELEPHONY ERROR] Cannot place outbound SIP call: SIP_TRUNK_ID / LIVEKIT_SIP_OUTBOUND_TRUNK_ID is not configured."
        )
        raise ValueError(
            "LIVEKIT_SIP_OUTBOUND_TRUNK_ID environment variable must be set to place outbound SIP calls."
        )

    lk_client = lk_api.LiveKitAPI(
        url=cfg.livekit.url,
        api_key=cfg.livekit.api_key,
        api_secret=cfg.livekit.api_secret,
    )

    try:
        meta_str = json.dumps(metadata, ensure_ascii=False) if metadata else ""
        sip_req = lk_api.CreateSIPParticipantRequest(
            sip_trunk_id=trunk_id,
            sip_call_to=phone_number,
            room_name=room_name,
            participant_identity=participant_identity,
            participant_name=participant_name,
            participant_metadata=meta_str,
            wait_until_answered=True,
            media_encryption=lk_api.SIP_MEDIA_ENCRYPT_ALLOW,
        )

        logger.info(
            "[TELEPHONY] Creating SIP participant for '%s' in room '%s' using trunk '%s'...",
            phone_number,
            room_name,
            trunk_id,
        )
        sip_info = await lk_client.sip.create_sip_participant(sip_req)
        logger.info(
            "[TELEPHONY] SIP participant created successfully! Participant ID: %s",
            getattr(sip_info, "sip_call_id", "created"),
        )
        return sip_info
    finally:
        await lk_client.aclose()
