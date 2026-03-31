"""Audit Log — SQLite-based event logging for compiles and queries.

Every compile and query is logged by default. The audit log records:
- Timestamp
- Event type (compile | query)
- User (optional identifier)
- Details (source path, question, CKUs used, etc.)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLog:
    """SQLite-backed audit log for noRAG operations."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL,
                event     TEXT    NOT NULL,
                user      TEXT    DEFAULT '',
                details   TEXT    DEFAULT '{}'
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_event
            ON audit_events(event)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
            ON audit_events(timestamp)
        """)
        self._conn.commit()

    def log_compile(
        self,
        source: str,
        status: str,
        user: str = "",
        roles: list[str] | None = None,
    ) -> int:
        """Log a compilation event. Returns the event ID."""
        details = {
            "source": source,
            "status": status,
            "roles": roles or [],
        }
        return self._insert("compile", user, details)

    def log_query(
        self,
        question: str,
        cku_ids: list[str],
        sources: list[str],
        user: str = "",
        user_role: str = "",
    ) -> int:
        """Log a query event. Returns the event ID."""
        details = {
            "question": question,
            "cku_ids": cku_ids,
            "sources": sources,
            "user_role": user_role,
        }
        return self._insert("query", user, details)

    def list_events(
        self,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List audit events, newest first."""
        if event_type:
            rows = self._conn.execute(
                "SELECT * FROM audit_events WHERE event = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (event_type, limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM audit_events ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "event": row["event"],
                "user": row["user"],
                "details": json.loads(row["details"]),
            }
            for row in rows
        ]

    def count(self, event_type: str | None = None) -> int:
        """Count audit events."""
        if event_type:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM audit_events WHERE event = ?",
                (event_type,),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM audit_events"
            ).fetchone()
        return row["n"]

    def _insert(self, event: str, user: str, details: dict) -> int:
        cur = self._conn.execute(
            "INSERT INTO audit_events (timestamp, event, user, details) VALUES (?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                event,
                user,
                json.dumps(details),
            ),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def close(self) -> None:
        self._conn.close()
