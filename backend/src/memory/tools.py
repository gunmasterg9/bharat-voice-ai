"""
Bharat Voice AI — Memory Agent Tools Module

Exposes LiveKit function tools for persistent SQLite memory:
- lookup_caller
- save_caller_memory
- forget_caller
"""

from __future__ import annotations

import json
from typing import Any

from livekit.agents import RunContext, function_tool

from agent.logger import COMPONENT_AGENT, get_logger
from memory.memory_service import SENSITIVE_KEYWORDS, get_memory_service

logger = get_logger(COMPONENT_AGENT)


@function_tool
async def lookup_caller_tool(agent: Any, context: RunContext, user_id: str) -> str:
    """
    Retrieve stored caller profile from SQLite database.

    Args:
        agent: The active BharatVoiceAgent instance.
        user_id: The unique caller identifier.

    Returns:
        JSON summary of caller profile or 'PROFILE_NOT_FOUND'.
    """
    db_memory = get_memory_service()
    if not user_id or str(user_id).lower() in [
        "anonymous",
        "user",
        "default_user",
        "caller",
    ]:
        user_id = agent.user_id

    logger.info("[MEMORY] LOOKUP START for user_id: %s", user_id)
    user = db_memory.get_user(user_id)
    if not user:
        logger.info("[MEMORY] LOOKUP NOT FOUND for user_id: %s", user_id)
        return "PROFILE_NOT_FOUND"

    logger.info("[MEMORY] LOOKUP FOUND profile for user_id: %s", user_id)
    profile_summary = {
        "name": user.get("name"),
        "language_preference": user.get("language_preference"),
        "relevant_facts": user.get("facts", {}),
        "last_interaction": user.get("last_interaction"),
    }
    return json.dumps(profile_summary, ensure_ascii=False)


@function_tool
async def save_caller_memory_tool(
    agent: Any,
    context: RunContext,
    user_id: str,
    name: str | None = None,
    language_preference: str | None = None,
    facts: str | None = None,
    user_consent: bool = False,
) -> str:
    """
    Persist caller information to SQLite database after explicit user consent.

    Args:
        agent: The active BharatVoiceAgent instance.
        user_id: The persistent caller identifier.
        name: Caller's name if voluntarily provided and consented.
        language_preference: Preferred language (e.g. 'Hindi', 'Gujarati', 'English').
        facts: Non-sensitive caller facts as a string or JSON string.
        user_consent: MUST be set to True only after the caller explicitly grants permission.
    """
    logger.info(
        "[MEMORY] SAVE START for user_id: %s, consent=%s", user_id, user_consent
    )

    if not user_consent:
        logger.warning("[MEMORY] SAVE REJECTED: missing explicit user_consent")
        return "Action blocked: Caller information can only be saved after explicit user consent."

    db_memory = get_memory_service()
    if not user_id or str(user_id).lower() in [
        "anonymous",
        "user",
        "default_user",
        "caller",
    ]:
        user_id = agent.user_id

    # Enforce safety check against sensitive credentials
    combined_check = f"{name or ''} {facts or ''}".lower()
    if any(kw in combined_check for kw in SENSITIVE_KEYWORDS):
        logger.warning("[MEMORY] SAVE REJECTED: sensitive information detected")
        return "Action blocked: Cannot save sensitive credentials (PINs, passwords, OTPs, bank/card details)."

    parsed_facts = {}
    if facts:
        try:
            parsed_facts = json.loads(facts)
        except Exception:
            parsed_facts = {"general_preference": facts}

    # Auto-detect language preference from recent user turns if missing
    if (
        not language_preference
        and hasattr(agent, "memory")
        and agent.memory
        and agent.memory.turns
    ):
        user_turns = [t for t in agent.memory.turns if t.role == "user" and t.language]
        if user_turns:
            last_lang = user_turns[-1].language
            lang_map = {
                "hi": "Hindi",
                "gu": "Gujarati",
                "hinglish": "Hinglish",
                "gujlish": "Gujlish",
                "en": "English",
            }
            language_preference = lang_map.get(last_lang, "Hindi")

    updated_user = db_memory.save_user_profile(
        user_id=user_id,
        name=name,
        language_preference=language_preference,
        facts=parsed_facts,
    )

    if updated_user:
        logger.info("[MEMORY] SAVE SUCCESS for user_id: %s", user_id)
        logger.info("[MEMORY] COMMIT SUCCESS for user_id: %s", user_id)
        return "Successfully saved caller information for future conversations."

    return "Failed to save caller profile due to a database error."


@function_tool
async def forget_caller_tool(
    agent: Any,
    context: RunContext,
    user_id: str,
    user_confirmation: bool = False,
) -> str:
    """
    Delete stored caller profile completely from SQLite upon explicit user confirmation.

    Args:
        agent: The active BharatVoiceAgent instance.
        user_id: The unique caller identifier.
        user_confirmation: MUST be set to True only after user explicitly confirms deletion.
    """
    logger.info(
        "[MEMORY] DELETE REQUEST for user_id: %s, confirmation=%s",
        user_id,
        user_confirmation,
    )

    if not user_confirmation:
        return "Action blocked: Deletion requires explicit user confirmation."

    db_memory = get_memory_service()
    if not user_id or str(user_id).lower() in [
        "anonymous",
        "user",
        "default_user",
        "caller",
    ]:
        user_id = agent.user_id

    success = db_memory.delete_user(user_id)
    if success:
        logger.info("[MEMORY] DELETE SUCCESS for user_id: %s", user_id)
        return "Done. I've removed your saved information."

    return "No stored profile found to delete or database operation failed."


@function_tool
async def update_outbound_consent_tool(
    agent: Any,
    context: RunContext,
    consent: bool,
    opt_out: bool = False,
) -> str:
    """
    Update the caller's consent for receiving proactive outbound weather alert calls.

    Args:
        agent: The active BharatVoiceAgent instance.
        consent: True if the user agrees to receive outbound calls, False otherwise.
        opt_out: Set to True if the user explicitly asks to stop receiving calls ("Stop calling me", "Don't call me again", "મને ફરી ફોન ન કરશો").
    """
    user_id = agent.user_id
    db_memory = getattr(agent, "db_memory", None) or get_memory_service()

    if opt_out:
        consent = False

    db_memory.update_outbound_consent(
        user_id=user_id, consent=consent, opted_out=opt_out
    )

    if opt_out or not consent:
        logger.info("[TOOLS] User '%s' OPTED OUT of outbound alert calls.", user_id)
        return "Understood. I have updated your preferences and will not place future alert calls to you."

    logger.info("[TOOLS] User '%s' CONSENTED to outbound alert calls.", user_id)
    return "Thank you! I have enabled weather alert calls for your saved location."


@function_tool
async def end_call_tool(
    agent: Any,
    context: RunContext,
    reason: str = "task_complete",
) -> str:
    """
    Gracefully disconnect the phone call when the conversation is finished, after opt-out, or after voicemail delivery.

    Args:
        agent: The active BharatVoiceAgent instance.
        reason: Reason for ending the call (e.g. 'user_opt_out', 'task_complete', 'voicemail_delivered').
    """
    logger.info("[TOOLS] Agent initiated call disconnect: reason='%s'", reason)
    try:
        if hasattr(agent, "room") and agent.room and hasattr(agent.room, "disconnect"):
            await agent.room.disconnect()
            logger.info(
                "[TOOLS] Room disconnected successfully via agent.room.disconnect()"
            )
        elif (
            hasattr(agent, "_active_session")
            and agent._active_session
            and hasattr(agent._active_session, "aclose")
        ):
            await agent._active_session.aclose()
            logger.info(
                "[TOOLS] Session closed successfully via agent._active_session.aclose()"
            )
        elif (
            hasattr(context, "session")
            and context.session
            and hasattr(context.session, "aclose")
        ):
            await context.session.aclose()
            logger.info(
                "[TOOLS] Session closed successfully via context.session.aclose()"
            )
    except Exception as exc:
        logger.warning("[TOOLS] Error during call disconnect: %s", exc)

    return "Call termination sequence initiated."


@function_tool
async def create_escalation_tool(
    agent: Any,
    context: RunContext,
    reason: str,
    summary: str,
    what_was_checked: str | None = None,
    urgency: str = "LOW",
    preferred_follow_up: str | None = "phone",
    user_permission: bool = False,
    name: str | None = None,
    language: str | None = None,
) -> str:
    """
    Create a human-help request after explicit caller permission.

    Args:
        agent: Active BharatVoiceAgent instance.
        reason: Explanation of why human help is needed (e.g. 'Weather data unavailable' or 'User explicitly requested human assistance').
        summary: Short concise human summary (WHO needs help, WHAT happened, WHAT agent checked, URGENCY, LANGUAGE, PREFERRED FOLLOW-UP METHOD).
        what_was_checked: Description of tools or steps already attempted.
        urgency: Urgency level ('LOW', 'MEDIUM', 'HIGH'). Default is 'LOW'.
        preferred_follow_up: Preferred contact method (default 'phone').
        user_permission: MUST be set to True only after explicit user agreement.
        name: Caller name if provided.
        language: Preferred language of caller.
    """
    user_id = getattr(agent, "user_id", "default_user")
    db_memory = getattr(agent, "db_memory", None) or get_memory_service()
    current_state = getattr(agent, "permission_state", "NOT_ASKED")

    logger.info(
        "[ESCALATION] Permission check: state='%s', user_permission=%s",
        current_state,
        user_permission,
    )

    agent.tool_used = "create_escalation"
    agent.primary_intent = "escalation"
    agent.task_started = True

    if current_state != "APPROVED" or not user_permission:
        logger.warning(
            "[ESCALATION] create_escalation blocked: state='%s', user_permission=%s",
            current_state,
            user_permission,
        )
        agent.tool_success = False
        agent.task_failed = True
        agent.failure_reason = "Escalation requested without caller permission"
        return json.dumps(
            {
                "success": False,
                "reason": "USER_PERMISSION_REQUIRED",
                "error": "permission_denied",
                "message": "Action blocked: Escalation requires explicit caller permission (permission_state is not APPROVED).",
            },
            ensure_ascii=False,
        )

    logger.info("[ESCALATION] Creating request")
    try:
        res = db_memory.create_escalation(
            user_id=user_id,
            reason=reason,
            summary=summary,
            what_was_checked=what_was_checked,
            urgency=urgency,
            preferred_follow_up=preferred_follow_up,
            name=name,
            language=language,
            user_permission=user_permission,
        )
        ref_id = res.get("reference_id", "ESC-UNKNOWN")
        logger.info("[ESCALATION] Reference ID: %s", ref_id)
        logger.info("[TOOLS] create_escalation result for user %s: %s", user_id, res)

        # Update agent state machine based on tool result
        if res.get("success"):
            agent.escalation_state = "ESCALATION_CREATED"
            agent.active_reference_id = ref_id
            agent.escalation_created = True
            agent.tool_success = True
            agent.task_completed = True
            agent.success_reason = (
                f"Human escalation created successfully (ref={ref_id})"
            )
            res["state"] = "ESCALATION_CREATED"
            logger.info(
                "[ESCALATION] State locked: ESCALATION_CREATED (ref=%s)", ref_id
            )
        else:
            agent.escalation_state = "ESCALATION_FAILED"
            agent.tool_success = False
            agent.task_failed = True
            agent.failure_reason = (
                res.get("message") or "Database error creating escalation"
            )
            res["state"] = "ESCALATION_FAILED"
            logger.warning("[ESCALATION] State: ESCALATION_FAILED")

        return json.dumps(res, ensure_ascii=False)
    except Exception as exc:
        logger.error("[TOOLS] Unexpected error creating escalation: %s", exc)
        agent.escalation_state = "ESCALATION_FAILED"
        agent.tool_success = False
        agent.task_failed = True
        agent.failure_reason = str(exc)
        return json.dumps(
            {
                "success": False,
                "error": "tool_failure",
                "state": "ESCALATION_FAILED",
                "message": "Sorry, I couldn't create the human-help request right now. Please try again later.",
            },
            ensure_ascii=False,
        )


@function_tool
async def switch_language_tool(
    agent: Any,
    context: RunContext,
    target_language: str,
) -> str:
    """
    Update active conversation language when user explicitly requests a language change.

    Args:
        agent: Active BharatVoiceAgent instance.
        target_language: Requested language ('Hindi', 'Gujarati', 'English').
    """
    lang_clean = str(target_language or "").strip().lower()
    if "hind" in lang_clean or "हिंदी" in lang_clean or "हिन्दी" in lang_clean:
        normalized = "Hindi"
        confirmation = "ठीक है। अब मैं आपसे हिंदी में बात करूंगी।"
    elif "gujarat" in lang_clean or "ગુજરાતી" in lang_clean:
        normalized = "Gujarati"
        confirmation = "બરાબર. હવે હું તમારી સાથે ગુજરાતીમાં વાત કરીશ."
    elif "eng" in lang_clean or "અંગ્રેજી" in lang_clean or "अंग्रेजी" in lang_clean:
        normalized = "English"
        confirmation = "Sure, I will speak with you in English now."
    else:
        normalized = "English"
        confirmation = "Sure, I will speak with you in English now."

    if hasattr(agent, "set_active_language"):
        agent.set_active_language(normalized)
    elif hasattr(agent, "active_language"):
        agent.active_language = normalized

    user_id = getattr(agent, "user_id", "default_user")
    db_memory = getattr(agent, "db_memory", None) or get_memory_service()
    if user_id and db_memory:
        user_profile = db_memory.get_user(user_id)
        if user_profile:
            db_memory.update_language_preference(user_id, normalized)

    logger.info(
        "[TOOLS] switch_language_tool: active_language set to '%s' for user_id '%s'",
        normalized,
        user_id,
    )
    return json.dumps(
        {
            "success": True,
            "active_language": normalized,
            "confirmation": confirmation,
            "message": f"Active language switched to {normalized}. Confirm to user using: {confirmation}",
        },
        ensure_ascii=False,
    )
