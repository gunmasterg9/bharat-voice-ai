"""
Bharat Voice AI — Conversation Memory Store

Provides persistent conversation history and session memory management.
Stores conversation turns, user context, and preferences to disk (JSON/SQLite).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from agent.logger import COMPONENT_AGENT, get_logger

logger = get_logger(COMPONENT_AGENT)

DEFAULT_MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "memory"


@dataclass
class ConversationTurn:
    """Represents a single turn in a voice conversation."""

    role: str
    content: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    language: str | None = None


@dataclass
class SessionMemory:
    """Session state and history for a participant."""

    session_id: str
    user_id: str = "default_user"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    turns: list[ConversationTurn] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


class ConversationMemoryStore:
    """
    Manages loading, persisting, and querying conversation history.
    """

    def __init__(self, memory_dir: Path | str = DEFAULT_MEMORY_DIR) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.active_sessions: dict[str, SessionMemory] = {}

    def get_or_create_session(
        self, session_id: str, user_id: str = "default_user"
    ) -> SessionMemory:
        """Get active session memory or create a new one."""
        if session_id not in self.active_sessions:
            filepath = self._get_filepath(session_id)
            if filepath.exists():
                session = self._load_from_file(filepath)
            else:
                session = SessionMemory(session_id=session_id, user_id=user_id)
            self.active_sessions[session_id] = session

        return self.active_sessions[session_id]

    def add_turn(
        self, session_id: str, role: str, content: str, language: str | None = None
    ) -> None:
        """Add a user or assistant turn to the conversation history."""
        session = self.get_or_create_session(session_id)
        turn = ConversationTurn(role=role, content=content, language=language)
        session.turns.append(turn)
        logger.info(
            "Added %s turn to session %s (total turns: %d)",
            role,
            session_id,
            len(session.turns),
        )
        self.save_session(session_id)

    def get_formatted_history(self, session_id: str, max_turns: int = 10) -> str:
        """Get formatted conversation history string for context injection."""
        session = self.get_or_create_session(session_id)
        recent_turns = session.turns[-max_turns:]
        if not recent_turns:
            return ""

        formatted_lines = ["--- Conversation History ---"]
        for turn in recent_turns:
            role_label = "User" if turn.role == "user" else "Assistant"
            formatted_lines.append(f"{role_label}: {turn.content}")
        return "\n".join(formatted_lines)

    def save_session(self, session_id: str) -> None:
        """Persist session memory to JSON file."""
        if session_id not in self.active_sessions:
            return

        session = self.active_sessions[session_id]
        filepath = self._get_filepath(session_id)
        try:
            data = asdict(session)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Persisted session memory to %s", filepath)
        except Exception as exc:
            logger.error(
                "Failed to save session memory for %s: %s", session_id, str(exc)
            )

    def _get_filepath(self, session_id: str) -> Path:
        sanitized_id = "".join(
            c if c.isalnum() or c in ("-", "_") else "_" for c in session_id
        )
        return self.memory_dir / f"{sanitized_id}.json"

    def _load_from_file(self, filepath: Path) -> SessionMemory:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        turns = [ConversationTurn(**t) for t in data.get("turns", [])]
        return SessionMemory(
            session_id=data.get("session_id", "unknown"),
            user_id=data.get("user_id", "default_user"),
            created_at=data.get("created_at", ""),
            turns=turns,
            metadata=data.get("metadata", {}),
        )


# Global singleton instance
memory_store = ConversationMemoryStore()
