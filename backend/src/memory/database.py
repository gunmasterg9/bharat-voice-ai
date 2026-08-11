"""
Bharat Voice AI — SQLite Database Module

Manages persistent SQLite storage at data/bharat_voice.db.
Survives process restarts, terminal restarts, and application restarts.
Enforces safe parameterized SQL execution, WAL journal mode, and transaction context management.
"""

import sqlite3
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from agent.logger import COMPONENT_AGENT, get_logger

logger = get_logger(COMPONENT_AGENT)

DEFAULT_DB_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "bharat_voice.db"
)


class Database:
    """SQLite Database manager with connection pooling and context safety."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provide a transactional database connection context manager."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            isolation_level=None,  # Autocommit mode managed explicitly
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for concurrent access safety
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")

        try:
            yield conn
        except Exception as exc:
            logger.error("Database transaction rollback due to error: %s", str(exc))
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema and perform migrations if needed."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            name TEXT,
            language_preference TEXT,
            facts TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_interaction TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS outbound_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            phone_hash TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            answered_at TEXT,
            ended_at TEXT,
            retry_count INTEGER DEFAULT 0,
            failure_code TEXT,
            failure_reason TEXT
        );
        """
        with self.get_connection() as conn:
            conn.executescript(schema_sql)

            # Perform safe column additions on existing 'users' table
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users);")
            existing_cols = {row[1] for row in cursor.fetchall()}

            new_columns = [
                ("phone_number", "TEXT"),
                ("phone_verified", "INTEGER DEFAULT 0"),
                ("outbound_call_consent", "INTEGER DEFAULT 0"),
                ("outbound_call_enabled", "INTEGER DEFAULT 1"),
                ("preferred_call_language", "TEXT"),
                ("last_outbound_call", "TEXT"),
                ("last_outbound_reason", "TEXT"),
                ("opted_out", "INTEGER DEFAULT 0"),
            ]

            for col_name, col_type in new_columns:
                if col_name not in existing_cols:
                    cursor.execute(
                        f"ALTER TABLE users ADD COLUMN {col_name} {col_type};"
                    )

        logger.info("Memory database initialized & schema updated: %s", self.db_path)

    def execute_read(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        """Execute a read query with parameterized inputs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return cursor.fetchall()

    def execute_write(self, query: str, params: Iterable[Any] = ()) -> int:
        """Execute a write query (INSERT/UPDATE/DELETE) with parameterized inputs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION;")
            cursor.execute(query, tuple(params))
            rowcount = cursor.rowcount
            cursor.execute("COMMIT;")
            return rowcount


# Singleton database instance
_db_instance: Database | None = None


def reset_db_singleton() -> None:
    """Reset global DB singleton instance for clean test isolation."""
    global _db_instance
    _db_instance = None


def get_db(db_path: Path | str | None = None) -> Database:
    """Get or create singleton Database instance."""
    global _db_instance
    if db_path is not None:
        _db_instance = Database(db_path)
    elif _db_instance is None or not _db_instance.db_path.parent.exists():
        _db_instance = Database(DEFAULT_DB_PATH)
    return _db_instance
