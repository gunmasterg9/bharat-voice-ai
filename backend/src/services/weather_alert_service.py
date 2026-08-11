"""
Bharat Voice AI — Weather Alert Decision Service

Evaluates weather data against user profile settings and system guardrails
(thresholds, consent, calling hours, duplicate call suppression).
"""

import re
from datetime import datetime, timezone
from typing import Any

from agent.config import Settings, load_settings
from agent.logger import COMPONENT_AGENT, get_logger
from memory.memory_service import MemoryService, mask_phone_number

logger = get_logger(COMPONENT_AGENT)


def validate_e164_phone(phone_number: str | None) -> tuple[bool, str]:
    """
    Validate phone number format (must be E.164 compliant, e.g. +919876543210).

    Returns:
        tuple (is_valid, cleaned_phone_or_error_message)
    """
    if not phone_number:
        return False, "Phone number is empty or missing."

    clean_phone = re.sub(r"[\s\-\(\)]", "", str(phone_number).strip())
    e164_pattern = r"^\+[1-9]\d{1,14}$"

    if not re.match(e164_pattern, clean_phone):
        return (
            False,
            f"Phone number '{mask_phone_number(clean_phone)}' is not valid E.164 format (must start with '+' followed by country code, e.g. +919876543210).",
        )

    return True, clean_phone


class WeatherAlertService:
    """Evaluates whether an outbound weather alert call should be placed to a user."""

    def __init__(
        self,
        settings: Settings | None = None,
        memory_service: MemoryService | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.memory = memory_service

    def should_call_user(
        self,
        weather_data: dict[str, Any],
        user_profile: dict[str, Any],
        current_dt: datetime | None = None,
    ) -> tuple[bool, str]:
        """
        Evaluate if an outbound alert call should be placed to the user.

        Args:
            weather_data: Structured weather dictionary from WeatherService.
            user_profile: User profile dictionary from MemoryService.
            current_dt: Optional datetime object for testing calling hours.

        Returns:
            tuple (should_call: bool, reason_or_rejection_cause: str)
        """
        user_id = user_profile.get("user_id", "unknown")

        # 1. Opt-out & consent check
        if user_profile.get("opted_out"):
            logger.info(
                "[ALERT DECISION] User '%s' has explicitly opted out of calls.", user_id
            )
            return False, "user_opted_out"

        if not user_profile.get("outbound_call_consent"):
            logger.info(
                "[ALERT DECISION] User '%s' has not given outbound call consent.",
                user_id,
            )
            return False, "no_outbound_consent"

        if not user_profile.get("outbound_call_enabled", True):
            logger.info(
                "[ALERT DECISION] Outbound calls are disabled for user '%s'.", user_id
            )
            return False, "outbound_calls_disabled"

        # 2. Phone number check
        raw_phone = user_profile.get("phone_number")
        is_valid, phone_result = validate_e164_phone(raw_phone)
        if not is_valid:
            logger.warning(
                "[ALERT DECISION] User '%s' has invalid phone number: %s",
                user_id,
                phone_result,
            )
            return False, f"invalid_phone: {phone_result}"

        # 3. Calling hours check (e.g., 08:00 to 20:00 local time)
        now = current_dt or datetime.now()
        start_hour = self.settings.telephony.outbound_call_start_hour
        end_hour = self.settings.telephony.outbound_call_end_hour

        if not (start_hour <= now.hour < end_hour):
            logger.info(
                "[ALERT DECISION] Current hour %d is outside calling hours (%d:00 - %d:00).",
                now.hour,
                start_hour,
                end_hour,
            )
            return False, f"outside_calling_hours: hour={now.hour}"

        # 4. Weather threshold check
        precip_prob = weather_data.get("precipitation_probability", 0)
        condition = str(weather_data.get("condition", "")).lower()
        threshold = self.settings.telephony.weather_alert_rain_threshold

        is_rain_alert = precip_prob >= threshold
        is_severe_weather = any(
            kw in condition
            for kw in ["thunderstorm", "heavy rain", "torrential", "hail", "violent"]
        )

        if not (is_rain_alert or is_severe_weather):
            logger.info(
                "[ALERT DECISION] Weather condition for user '%s' does not meet threshold (prob=%d%% vs %d%%, condition='%s').",
                user_id,
                precip_prob,
                threshold,
                condition,
            )
            return (
                False,
                f"weather_below_threshold: precip={precip_prob}%, condition={condition}",
            )

        reason = (
            f"severe_weather_alert: {condition}"
            if is_severe_weather
            else f"high_rain_probability: {precip_prob}%"
        )

        # 5. Duplicate alert prevention
        last_reason = user_profile.get("last_outbound_reason")
        last_call_iso = user_profile.get("last_outbound_call")
        if last_reason == reason and last_call_iso:
            try:
                last_call_dt = datetime.fromisoformat(last_call_iso)
                if last_call_dt.tzinfo is None:
                    last_call_dt = last_call_dt.replace(tzinfo=timezone.utc)
                now_utc = datetime.now(timezone.utc)
                hours_since = (now_utc - last_call_dt).total_seconds() / 3600.0
                if hours_since < 24.0:
                    logger.info(
                        "[ALERT DECISION] Duplicate alert suppressed for user '%s'. Last call was %.1f hours ago.",
                        user_id,
                        hours_since,
                    )
                    return (
                        False,
                        f"duplicate_alert_suppressed: last_call={hours_since:.1f}h_ago",
                    )
            except Exception as exc:
                logger.warning(
                    "[ALERT DECISION] Error parsing last_outbound_call timestamp: %s",
                    exc,
                )

        logger.info(
            "[ALERT DECISION] Outbound alert APPROVED for user '%s': %s (phone=%s)",
            user_id,
            reason,
            mask_phone_number(phone_result),
        )
        return True, reason
