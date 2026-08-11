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
            logger.info("[TOOLS] Room disconnected successfully via agent.room.disconnect()")
        elif hasattr(agent, "_active_session") and agent._active_session and hasattr(agent._active_session, "aclose"):
            await agent._active_session.aclose()
            logger.info("[TOOLS] Session closed successfully via agent._active_session.aclose()")
        elif hasattr(context, "session") and context.session and hasattr(context.session, "aclose"):
            await context.session.aclose()
            logger.info("[TOOLS] Session closed successfully via context.session.aclose()")
    except Exception as exc:
        logger.warning("[TOOLS] Error during call disconnect: %s", exc)

    return "Call termination sequence initiated."
