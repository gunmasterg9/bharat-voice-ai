"""
Bharat Voice AI — Outbound Call Manager

Orchestrates full outbound phone calls:
1. Validates phone number, consent, calling hours, and duplicate rules.
2. Applies TEST_MODE guardrails (redirects to test phone if active).
3. Generates opaque room names (`bharat-outbound-{hash}-{timestamp}`).
4. Dispatches agent and dials SIP participant.
5. Logs call lifecycle events to SQLite database.
"""

import hashlib
import time
from datetime import datetime, timezone

from agent.config import Settings, load_settings
from agent.logger import COMPONENT_AGENT, get_logger
from memory.memory_service import MemoryService, get_memory_service, mask_phone_number
from services.weather_alert_service import WeatherAlertService, validate_e164_phone
from telephony.outbound import create_sip_participant, dispatch_agent_to_room

logger = get_logger(COMPONENT_AGENT)


class OutboundCallManager:
    """High-level manager for initiating and tracking outbound AI voice calls."""

    def __init__(
        self,
        settings: Settings | None = None,
        memory_service: MemoryService | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.memory = memory_service or get_memory_service()
        self.alert_service = WeatherAlertService(
            settings=self.settings, memory_service=self.memory
        )

    async def place_outbound_call(
        self,
        phone_number: str,
        user_id: str,
        reason: str = "weather_alert",
        language: str | None = None,
        weather_data: dict | None = None,
        bypass_decision_checks: bool = False,
    ) -> dict:
        """
        Place an outbound voice AI call to a user.

        Returns:
            Structured dictionary with 'success': True/False, 'call_id', 'room_name', 'status', and 'message'.
        """
        user_profile = self.memory.get_user(user_id) or {"user_id": user_id}
        target_phone = phone_number or user_profile.get("phone_number", "")
        target_name = user_profile.get("name", "Valued User")
        target_lang = (
            language
            or user_profile.get("language_preference")
            or user_profile.get("preferred_call_language")
            or "Gujarati"
        )

        # 1. TEST MODE Guardrail Enforcement
        if self.settings.telephony.outbound_test_mode:
            test_phone = self.settings.telephony.outbound_test_phone_number
            if not test_phone:
                logger.error(
                    "[CALL MANAGER] OUTBOUND_TEST_MODE is true but OUTBOUND_TEST_PHONE_NUMBER is not set in environment!"
                )
                return {
                    "success": False,
                    "status": "CONFIG_ERROR",
                    "message": "OUTBOUND_TEST_MODE is enabled but OUTBOUND_TEST_PHONE_NUMBER is missing.",
                }
            logger.info(
                "[CALL MANAGER TEST MODE] Redirecting call for '%s' (%s) -> TEST PHONE: %s",
                user_id,
                mask_phone_number(target_phone),
                mask_phone_number(test_phone),
            )
            target_phone = test_phone

        # 2. Validate E.164 phone number
        is_valid, phone_res = validate_e164_phone(target_phone)
        if not is_valid:
            logger.warning("[CALL MANAGER] Phone validation failed: %s", phone_res)
            return {
                "success": False,
                "status": "INVALID_PHONE",
                "message": phone_res,
            }

        # 3. Decision & Guardrail Checks (unless explicitly bypassed for dev script)
        if not bypass_decision_checks and weather_data:
            should_call, decision_reason = self.alert_service.should_call_user(
                weather_data=weather_data, user_profile=user_profile
            )
            if not should_call:
                logger.info(
                    "[CALL MANAGER] Call blocked by alert decision engine: %s",
                    decision_reason,
                )
                return {
                    "success": False,
                    "status": "BLOCKED_BY_GUARDRAIL",
                    "message": f"Call blocked: {decision_reason}",
                }

        # 4. Generate unique opaque room name and call_id
        timestamp = int(time.time())
        user_hash = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:8]
        room_name = f"bharat-outbound-{user_hash}-{timestamp}"
        call_id = f"call_{user_hash}_{timestamp}"
        started_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "[CALL MANAGER] Initiating outbound call (call_id=%s, room=%s, user=%s, phone=%s, lang=%s)...",
            call_id,
            room_name,
            user_id,
            mask_phone_number(target_phone),
            target_lang,
        )

        # Log initial QUEUED status to DB
        self.memory.record_outbound_call(
            call_id=call_id,
            user_id=user_id,
            phone_number=target_phone,
            reason=reason,
            status="QUEUED",
            started_at=started_at,
        )

        call_metadata = {
            "call_type": "outbound_weather_alert",
            "call_id": call_id,
            "user_id": user_id,
            "user_name": target_name,
            "reason": reason,
            "language": target_lang,
            "weather_data": weather_data or {},
        }

        try:
            # 5. Dispatch Agent process to room
            self.memory.record_outbound_call(
                call_id=call_id,
                user_id=user_id,
                phone_number=target_phone,
                reason=reason,
                status="DISPATCHING",
                started_at=started_at,
            )
            await dispatch_agent_to_room(
                room_name=room_name, metadata=call_metadata, settings=self.settings
            )

            # 6. Create SIP Participant to dial phone
            self.memory.record_outbound_call(
                call_id=call_id,
                user_id=user_id,
                phone_number=target_phone,
                reason=reason,
                status="DIALING",
                started_at=started_at,
            )
            sip_info = await create_sip_participant(
                room_name=room_name,
                phone_number=target_phone,
                participant_identity=target_phone,
                participant_name=target_name,
                metadata=call_metadata,
                settings=self.settings,
            )

            answered_at = datetime.now(timezone.utc).isoformat()
            self.memory.record_outbound_call(
                call_id=call_id,
                user_id=user_id,
                phone_number=target_phone,
                reason=reason,
                status="ANSWERED",
                started_at=started_at,
                answered_at=answered_at,
            )

            return {
                "success": True,
                "call_id": call_id,
                "room_name": room_name,
                "status": "ANSWERED",
                "message": f"Outbound call connected successfully to {mask_phone_number(target_phone)}.",
                "sip_info": str(sip_info),
            }

        except Exception as exc:
            logger.error(
                "[CALL MANAGER ERROR] Outbound call failed for call_id=%s: %s",
                call_id,
                str(exc),
            )
            ended_at = datetime.now(timezone.utc).isoformat()
            self.memory.record_outbound_call(
                call_id=call_id,
                user_id=user_id,
                phone_number=target_phone,
                reason=reason,
                status="FAILED",
                started_at=started_at,
                ended_at=ended_at,
                failure_code="CALL_INITIATION_ERROR",
                failure_reason=str(exc),
            )
            return {
                "success": False,
                "call_id": call_id,
                "room_name": room_name,
                "status": "FAILED",
                "message": f"Call initiation failed: {exc!s}",
            }
