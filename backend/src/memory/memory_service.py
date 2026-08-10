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
                "SELECT user_id, name, language_preference, facts, last_interaction, created_at, updated_at "
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
                    "SELECT user_id, name, language_preference, facts, last_interaction, created_at, updated_at "
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

            return {
                "user_id": row["user_id"],
                "name": row["name"],
                "language_preference": row["language_preference"],
                "facts": facts_dict,
                "last_interaction": row["last_interaction"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
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
