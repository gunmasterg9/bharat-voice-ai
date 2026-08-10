"""
Inspect Bharat Voice AI SQLite Database (data/bharat_voice.db).

Usage:
    uv run python -m memory.inspect_db
"""

from __future__ import annotations

import json
from pathlib import Path

from memory.database import DEFAULT_DB_PATH, Database


def inspect_database() -> None:
    """Print clean non-sensitive summary of stored user profiles in SQLite."""
    db_path = Path(DEFAULT_DB_PATH)
    print("=" * 60)
    print("BHARAT VOICE AI — SQLITE DATABASE INSPECTION")
    print(f"Location: {db_path}")
    print("=" * 60)

    if not db_path.exists():
        print(f"[ERROR] Database file does not exist at {db_path}")
        return

    db = Database(db_path)

    rows = db.execute_read(
        "SELECT user_id, name, language_preference, facts, last_interaction FROM users;"
    )

    print(f"\nUsers: {len(rows)}\n")

    for idx, r in enumerate(rows, 1):
        user_id = r["user_id"]
        name = r["name"] or "Not specified"
        lang = r["language_preference"] or "Not specified"
        facts_raw = r["facts"] or "{}"
        try:
            facts = json.loads(facts_raw)
        except Exception:
            facts = {}

        print(f"[{idx}] User ID: {user_id}")
        print(f"    Name: {name}")
        print(f"    Language Preference: {lang}")
        print(f"    Facts: {json.dumps(facts, ensure_ascii=False)}")
        print(f"    Last Interaction: {r['last_interaction']}")
        print("-" * 50)


if __name__ == "__main__":
    inspect_database()
