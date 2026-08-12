"""
Bharat Voice AI — Memory Service

Provides high-level CRUD operations over the SQLite database.
Handles caller profile loading, fact persistence, JSON serialization/deserialization,
sensitive information scrubbing, and deletion protocols.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.logger import COMPONENT_AGENT, get_logger
from memory.database import Database, get_db

logger = get_logger(COMPONENT_AGENT)


def mask_phone_number(phone: str | None) -> str:
    """Mask phone number for safe log printing (e.g. +919876543210 -> +91******3210)."""
    if not phone:
        return "<none>"
    phone_clean = str(phone).strip()
    if len(phone_clean) <= 6:
        return "***"
    prefix = phone_clean[:3]
    suffix = phone_clean[-4:]
    masked_len = len(phone_clean) - 7
    return f"{prefix}{'*' * max(3, masked_len)}{suffix}"


# Sensitive patterns that MUST NOT be stored in memory
SENSITIVE_KEYWORDS = {
    "password",
    "passwords",
    "otp",
    "otps",
    "pin",
    "pins",
    "bank",
    "bank_account",
    "account_number",
    "account_no",
    "id_number",
    "aadhaar",
    "pan_card",
    "voter_id",
    "driving_license",
    "credit_card",
    "debit_card",
    "card_number",
    "cvv",
    "token",
    "auth_token",
    "api_key",
    "secret",
    "medical_notes",
    "clinical_notes",
    "doctor_notes",
}


def scrub_sensitive_text(text: str | None) -> str:
    """
    Scrub passwords, OTPs, PINs, bank accounts, card numbers, API keys from free text.
    """
    if not text:
        return ""
    import re

    result = str(text)
    patterns = [
        (
            r"(?i)\b(password|passwords|passwd|otp|otps|pin|pins|cvv|api_key|api_secret|auth_token|token|card_number|account_number|bank_account|sip_password)\b(\s*[:=]|\s+is|\s+was|\s+code|\s+no|\s+number)?\s*['\"]?\w+['\"]?",
            r"\1: [REDACTED]",
        ),
        (r"\b\d{13,19}\b", "[REDACTED_CARD_OR_ACCOUNT]"),
        (r"\b\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}\b", "[REDACTED_CARD]"),
    ]
    for pat, repl in patterns:
        result = re.sub(pat, repl, result)
    return result


def sanitize_facts(facts: dict[str, Any]) -> dict[str, Any]:
    """
    Scrub sensitive credentials from facts dictionary before storage.

    Returns:
        Scrubbed facts dictionary with forbidden sensitive keys removed.
    """
    clean_facts = {}
    forbidden_value_patterns = [
        "password",
        "otp",
        "pin",
        "cvv",
        "credit card",
        "account number",
        "aadhaar",
        "pan number",
        "medical notes",
        "clinical notes",
        "doctor notes",
    ]
    for key, value in facts.items():
        key_lower = str(key).lower()
        if any(kw in key_lower for kw in SENSITIVE_KEYWORDS):
            logger.warning(
                "Blocked attempt to persist sensitive keyword in fact key: %s", key
            )
            continue

        val_str = str(value).lower()
        if any(pat in val_str for pat in forbidden_value_patterns):
            logger.warning(
                "Blocked attempt to persist sensitive value under key: %s", key
            )
            continue

        clean_facts[key] = value

    return clean_facts


class MemoryService:
    """Manages persistent caller profile records in SQLite."""

    def __init__(self, db: Database | None = None) -> None:
        self.db = db or get_db()

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        """
        Retrieve caller profile by user_id.

        Returns:
            Dictionary containing caller fields, or None if user not found.
        """
        if not user_id:
            return None

        try:
            logger.info("[MEMORY] User ID: %s", user_id)
            rows = self.db.execute_read(
                "SELECT user_id, name, language_preference, facts, last_interaction, created_at, updated_at, "
                "phone_number, phone_verified, outbound_call_consent, outbound_call_enabled, preferred_call_language, "
                "last_outbound_call, last_outbound_reason, opted_out "
                "FROM users WHERE user_id = ? OR name = ? ORDER BY CASE WHEN user_id = ? THEN 0 ELSE 1 END, last_interaction DESC;",
                (user_id, user_id, user_id),
            )
            if not rows and str(user_id).lower() in [
                "default_user",
                "caller_default_user",
                "caller",
                "user",
            ]:
                rows = self.db.execute_read(
                    "SELECT user_id, name, language_preference, facts, last_interaction, created_at, updated_at, "
                    "phone_number, phone_verified, outbound_call_consent, outbound_call_enabled, preferred_call_language, "
                    "last_outbound_call, last_outbound_reason, opted_out "
                    "FROM users ORDER BY last_interaction DESC LIMIT 1;"
                )

            if not rows:
                logger.info("[MEMORY] Lookup: NOT FOUND for user_id: %s", user_id)
                return None

            logger.info("[MEMORY] Lookup: FOUND profile for user_id: %s", user_id)
            row = rows[0]
            facts_raw = row["facts"] or "{}"
            try:
                facts_dict = json.loads(facts_raw)
            except Exception:
                facts_dict = {}

            # Helper function to access dict key or Row column safely
            def get_col(r, key, default=None):
                try:
                    return r[key] if r[key] is not None else default
                except (IndexError, KeyError):
                    return default

            return {
                "user_id": row["user_id"],
                "name": row["name"],
                "language_preference": row["language_preference"],
                "facts": facts_dict,
                "last_interaction": row["last_interaction"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "phone_number": get_col(row, "phone_number"),
                "phone_verified": bool(get_col(row, "phone_verified", 0)),
                "outbound_call_consent": bool(get_col(row, "outbound_call_consent", 0)),
                "outbound_call_enabled": bool(get_col(row, "outbound_call_enabled", 1)),
                "preferred_call_language": get_col(row, "preferred_call_language"),
                "last_outbound_call": get_col(row, "last_outbound_call"),
                "last_outbound_reason": get_col(row, "last_outbound_reason"),
                "opted_out": bool(get_col(row, "opted_out", 0)),
            }
        except Exception as exc:
            logger.error("Error retrieving user profile for %s: %s", user_id, str(exc))
            return None

    def save_user(
        self,
        user_id: str,
        name: str | None = None,
        language_preference: str | None = None,
        facts: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        """
        Create or update a complete caller profile.

        Args:
            user_id: Persistent caller identifier.
            name: Optional caller name.
            language_preference: Optional preferred language.
            facts: Optional facts dictionary or JSON string.

        Returns:
            Updated caller profile dictionary.
        """
        now = datetime.now(timezone.utc).isoformat()
        existing = self.get_user(user_id)

        # Merge facts if existing
        if isinstance(facts, str):
            try:
                parsed_facts = json.loads(facts)
            except Exception:
                parsed_facts = {}
        elif isinstance(facts, dict):
            parsed_facts = facts
        else:
            parsed_facts = {}

        clean_new_facts = sanitize_facts(parsed_facts)

        if existing:
            merged_facts = {**existing.get("facts", {}), **clean_new_facts}
            final_name = name if name is not None else existing.get("name")
            final_lang = (
                language_preference
                if language_preference is not None
                else existing.get("language_preference")
            )

            facts_json = json.dumps(merged_facts, ensure_ascii=False)
            self.db.execute_write(
                "UPDATE users SET name = ?, language_preference = ?, facts = ?, "
                "last_interaction = ?, updated_at = ? WHERE user_id = ?;",
                (final_name, final_lang, facts_json, now, now, user_id),
            )
        else:
            facts_json = json.dumps(clean_new_facts, ensure_ascii=False)
            self.db.execute_write(
                "INSERT INTO users (user_id, name, language_preference, facts, last_interaction, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?);",
                (user_id, name, language_preference, facts_json, now, now, now),
            )

        logger.info("Saved user profile successfully for user_id: %s", user_id)
        return self.get_user(user_id) or {}

    def update_user_facts(
        self, user_id: str, new_facts: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge and update caller facts."""
        clean_facts = sanitize_facts(new_facts)
        user = self.get_user(user_id)
        if not user:
            return self.save_user(user_id=user_id, facts=clean_facts)

        merged = {**user.get("facts", {}), **clean_facts}
        now = datetime.now(timezone.utc).isoformat()
        facts_json = json.dumps(merged, ensure_ascii=False)

        self.db.execute_write(
            "UPDATE users SET facts = ?, updated_at = ? WHERE user_id = ?;",
            (facts_json, now, user_id),
        )
        return self.get_user(user_id) or {}

    def update_language_preference(self, user_id: str, language: str) -> dict[str, Any]:
        """Update user's preferred language."""
        user = self.get_user(user_id)
        if not user:
            return self.save_user(user_id=user_id, language_preference=language)

        now = datetime.now(timezone.utc).isoformat()
        self.db.execute_write(
            "UPDATE users SET language_preference = ?, updated_at = ? WHERE user_id = ?;",
            (language, now, user_id),
        )
        return self.get_user(user_id) or {}

    def update_last_interaction(self, user_id: str) -> dict[str, Any] | None:
        """Update last_interaction timestamp for caller."""
        now = datetime.now(timezone.utc).isoformat()
        user = self.get_user(user_id)
        if not user:
            return None

        self.db.execute_write(
            "UPDATE users SET last_interaction = ?, updated_at = ? WHERE user_id = ?;",
            (now, now, user_id),
        )
        return self.get_user(user_id)

    def user_exists(self, user_id: str) -> bool:
        """Check if a user_id profile exists in SQLite."""
        if not user_id:
            return False
        rows = self.db.execute_read(
            "SELECT 1 FROM users WHERE user_id = ?;", (user_id,)
        )
        return len(rows) > 0

    def create_user(
        self,
        user_id: str,
        name: str | None = None,
        language_preference: str | None = None,
        facts: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        """Create a new user profile record in SQLite."""
        now = datetime.now(timezone.utc).isoformat()
        if isinstance(facts, str):
            try:
                parsed_facts = json.loads(facts)
            except Exception:
                parsed_facts = {}
        elif isinstance(facts, dict):
            parsed_facts = facts
        else:
            parsed_facts = {}

        clean_facts = sanitize_facts(parsed_facts)
        facts_json = json.dumps(clean_facts, ensure_ascii=False)

        self.db.execute_write(
            "INSERT INTO users (user_id, name, language_preference, facts, created_at, updated_at, last_interaction) "
            "VALUES (?, ?, ?, ?, ?, ?, ?);",
            (user_id, name, language_preference, facts_json, now, now, now),
        )
        logger.info("[MEMORY] Profile created for user_id: %s", user_id)
        return self.get_user(user_id) or {}

    def save_user_profile(
        self,
        user_id: str,
        name: str | None = None,
        language_preference: str | None = None,
        facts: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        """Explicit save alias for save_user/create_user."""
        return self.save_user(
            user_id=user_id,
            name=name,
            language_preference=language_preference,
            facts=facts,
        )

    def update_user_profile(
        self,
        user_id: str,
        name: str | None = None,
        language_preference: str | None = None,
        facts: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        """Explicit update alias for save_user."""
        return self.save_user(
            user_id=user_id,
            name=name,
            language_preference=language_preference,
            facts=facts,
        )

    def delete_user(self, user_id: str) -> bool:
        """
        Delete a caller profile completely from SQLite.

        Returns:
            True if row was deleted, False otherwise.
        """
        if not user_id:
            return False

        try:
            rowcount = self.db.execute_write(
                "DELETE FROM users WHERE user_id = ?;", (user_id,)
            )
            logger.info(
                "[MEMORY] Profile deleted for user_id: %s (rows: %d)", user_id, rowcount
            )
            return rowcount > 0
        except Exception as exc:
            logger.error("Error deleting user %s: %s", user_id, str(exc))
            return False

    def update_outbound_consent(
        self, user_id: str, consent: bool, opted_out: bool = False
    ) -> dict[str, Any]:
        """Update outbound call consent and opted_out flags for a user."""
        now = datetime.now(timezone.utc).isoformat()
        user = self.get_user(user_id)
        if not user:
            self.save_user(user_id=user_id)

        self.db.execute_write(
            "UPDATE users SET outbound_call_consent = ?, opted_out = ?, updated_at = ? WHERE user_id = ?;",
            (1 if consent else 0, 1 if opted_out else 0, now, user_id),
        )
        logger.info(
            "[MEMORY] Outbound consent updated for user_id '%s': consent=%s, opted_out=%s",
            user_id,
            consent,
            opted_out,
        )
        return self.get_user(user_id) or {}

    def update_user_phone(
        self, user_id: str, phone_number: str, verified: bool = False
    ) -> dict[str, Any]:
        """Update phone number for a user profile."""
        now = datetime.now(timezone.utc).isoformat()
        user = self.get_user(user_id)
        if not user:
            self.save_user(user_id=user_id)

        self.db.execute_write(
            "UPDATE users SET phone_number = ?, phone_verified = ?, updated_at = ? WHERE user_id = ?;",
            (phone_number, 1 if verified else 0, now, user_id),
        )
        logger.info(
            "[MEMORY] Phone number updated for user_id '%s': %s",
            user_id,
            mask_phone_number(phone_number),
        )
        return self.get_user(user_id) or {}

    def record_outbound_call(
        self,
        call_id: str,
        user_id: str,
        phone_number: str,
        reason: str,
        status: str,
        started_at: str | None = None,
        answered_at: str | None = None,
        ended_at: str | None = None,
        retry_count: int = 0,
        failure_code: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        """Record an outbound call event in the outbound_calls table and update user's last_outbound_call."""
        import hashlib

        phone_hash = (
            hashlib.sha256(phone_number.encode("utf-8")).hexdigest()[:16]
            if phone_number
            else "unknown"
        )
        now = datetime.now(timezone.utc).isoformat()
        start = started_at or now

        self.db.execute_write(
            "INSERT OR REPLACE INTO outbound_calls "
            "(call_id, user_id, phone_hash, reason, status, started_at, answered_at, ended_at, retry_count, failure_code, failure_reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (
                call_id,
                user_id,
                phone_hash,
                reason,
                status,
                start,
                answered_at,
                ended_at,
                retry_count,
                failure_code,
                failure_reason,
            ),
        )

        self.db.execute_write(
            "UPDATE users SET last_outbound_call = ?, last_outbound_reason = ?, updated_at = ? WHERE user_id = ?;",
            (now, reason, now, user_id),
        )
        logger.info(
            "[MEMORY] Outbound call logged: call_id=%s, user_id=%s, status=%s, reason=%s",
            call_id,
            user_id,
            status,
            reason,
        )

    # -----------------------------------------------------------------
    # Day 7 Human Help & Escalation Methods
    # -----------------------------------------------------------------

    def create_escalation(
        self,
        user_id: str,
        reason: str,
        summary: str,
        what_was_checked: str | None = None,
        urgency: str = "LOW",
        preferred_follow_up: str | None = "phone",
        name: str | None = None,
        language: str | None = None,
        user_permission: bool = False,
    ) -> dict[str, Any]:
        """
        Create a human-help escalation request in SQLite.

        Enforces explicit user permission, privacy filtering, duplicate request prevention,
        and dynamic reference ID generation in format ESC-YYYYMMDD-XXXX.
        """
        logger.info("[DB] Database path: %s", getattr(self.db, "db_path", "unknown"))
        logger.info("[ESCALATION] Human help intent detected")

        if not user_permission:
            logger.warning(
                "[ESCALATION] Creation blocked: explicit user_permission is False"
            )
            return {
                "success": False,
                "error": "permission_denied",
                "message": "Escalation request requires explicit user permission.",
            }

        # 1. Duplicate check: look for OPEN escalation for same user and matching reason
        clean_reason = scrub_sensitive_text(reason or "Human help requested")
        existing = self.db.execute_read(
            "SELECT reference_id, status FROM escalations "
            "WHERE user_id = ? AND status = 'OPEN' AND reason = ? ORDER BY created_at DESC LIMIT 1;",
            (user_id, clean_reason),
        )
        if existing:
            ref_id = existing[0]["reference_id"]
            logger.info(
                "[ESCALATION] Duplicate OPEN request found for user '%s', returning existing ref '%s'",
                user_id,
                ref_id,
            )
            return {
                "success": True,
                "reference_id": ref_id,
                "status": "OPEN",
                "is_duplicate": True,
            }

        # 2. Generate dynamic reference ID: ESC-YYYYMMDD-XXXX
        now_dt = datetime.now(timezone.utc)
        date_str = now_dt.strftime("%Y%m%d")
        count_rows = self.db.execute_read(
            "SELECT COUNT(*) as cnt FROM escalations WHERE reference_id LIKE ?;",
            (f"ESC-{date_str}-%",),
        )
        seq_num = (count_rows[0]["cnt"] if count_rows else 0) + 1
        reference_id = f"ESC-{date_str}-{seq_num:04d}"
        logger.info("[ESCALATION] Generated reference ID: %s", reference_id)

        # 3. Scrub sensitive fields
        clean_summary = scrub_sensitive_text(summary or "User requested human support.")
        clean_checked = scrub_sensitive_text(
            what_was_checked or "Voice agent initial triage."
        )
        clean_name = scrub_sensitive_text(name) if name else None
        clean_lang = scrub_sensitive_text(language) if language else None
        clean_urgency = (
            urgency.upper()
            if urgency and urgency.upper() in ["LOW", "MEDIUM", "HIGH"]
            else "LOW"
        )
        clean_follow_up = (
            scrub_sensitive_text(preferred_follow_up)
            if preferred_follow_up
            else "phone"
        )
        now_iso = now_dt.isoformat()

        # 4. Insert into SQLite
        try:
            logger.info("[DB] Escalation INSERT")
            self.db.execute_write(
                "INSERT INTO escalations "
                "(reference_id, user_id, name, language, reason, summary, what_was_checked, urgency, preferred_follow_up, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?);",
                (
                    reference_id,
                    user_id,
                    clean_name,
                    clean_lang,
                    clean_reason,
                    clean_summary,
                    clean_checked,
                    clean_urgency,
                    clean_follow_up,
                    now_iso,
                    now_iso,
                ),
            )
            logger.info("[DB] Escalation COMMIT successful")

            # 5. Verification step: read back record to confirm database write
            record = self.get_escalation_by_ref(reference_id)
            if not record:
                logger.error(
                    "[ESCALATION ERROR] Verification read failed for ref_id '%s'",
                    reference_id,
                )
                return {
                    "success": False,
                    "error": "database_verification_failed",
                    "message": "Failed to verify escalation record persistence in database.",
                }

            logger.info(
                "[DB] Escalation verification successful: ref_id=%s, status=%s",
                reference_id,
                record["status"],
            )
            logger.info("[ESCALATION] Request created successfully: %s", reference_id)
            return {
                "success": True,
                "reference_id": reference_id,
                "status": "OPEN",
            }
        except Exception as exc:
            logger.error(
                "[ESCALATION ERROR] Database write failed for user %s: %s", user_id, exc
            )
            return {
                "success": False,
                "error": "database_error",
                "message": "Failed to create escalation record in database.",
            }

    def get_escalations(
        self, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Retrieve stored escalation records ordered by created_at DESC."""
        try:
            if status:
                rows = self.db.execute_read(
                    "SELECT id, reference_id, user_id, name, language, reason, summary, what_was_checked, urgency, preferred_follow_up, status, created_at, updated_at "
                    "FROM escalations WHERE status = ? ORDER BY created_at DESC LIMIT ?;",
                    (status.upper(), limit),
                )
            else:
                rows = self.db.execute_read(
                    "SELECT id, reference_id, user_id, name, language, reason, summary, what_was_checked, urgency, preferred_follow_up, status, created_at, updated_at "
                    "FROM escalations ORDER BY created_at DESC LIMIT ?;",
                    (limit,),
                )
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.error("Error retrieving escalations: %s", exc)
            return []

    def get_escalation_by_ref(self, reference_id: str) -> dict[str, Any] | None:
        """Fetch a single escalation record by reference_id."""
        try:
            rows = self.db.execute_read(
                "SELECT id, reference_id, user_id, name, language, reason, summary, what_was_checked, urgency, preferred_follow_up, status, created_at, updated_at "
                "FROM escalations WHERE reference_id = ?;",
                (reference_id,),
            )
            return dict(rows[0]) if rows else None
        except Exception as exc:
            logger.error("Error retrieving escalation %s: %s", reference_id, exc)
            return None

    def update_escalation_status(
        self, reference_id: str, new_status: str
    ) -> dict[str, Any] | None:
        """Update escalation status (OPEN, IN_PROGRESS, RESOLVED)."""
        valid_statuses = ["OPEN", "IN_PROGRESS", "RESOLVED"]
        target_status = new_status.upper() if new_status else ""
        if target_status not in valid_statuses:
            logger.warning(
                "Invalid escalation status transition attempt: %s", new_status
            )
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        rowcount = self.db.execute_write(
            "UPDATE escalations SET status = ?, updated_at = ? WHERE reference_id = ?;",
            (target_status, now_iso, reference_id),
        )
        if rowcount > 0:
            logger.info(
                "Updated escalation %s status to %s", reference_id, target_status
            )
            return self.get_escalation_by_ref(reference_id)
        return None


# Singleton memory service
_memory_service_instance: MemoryService | None = None


def reset_memory_service_singleton() -> None:
    """Reset global MemoryService singleton instance for clean test isolation."""
    global _memory_service_instance
    _memory_service_instance = None


def get_memory_service(db: Database | None = None) -> MemoryService:
    """Get singleton MemoryService instance."""
    global _memory_service_instance
    if db is not None:
        _memory_service_instance = MemoryService(db)
    elif (
        _memory_service_instance is None
        or not _memory_service_instance.db.db_path.parent.exists()
    ):
        _memory_service_instance = MemoryService(get_db())
    return _memory_service_instance


def initialize_database(db_path: Path | str | None = None) -> Database:
    """Initialize persistent SQLite database file on disk."""
    db = get_db(db_path)
    logger.info("[MEMORY] DATABASE INITIALIZED at path: %s", db.db_path)
    return db
