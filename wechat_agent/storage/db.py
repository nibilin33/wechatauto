from __future__ import annotations

"""
Optional SQLite storage for run summaries and message history.

The schema is intentionally minimal; the canonical audit trail is the JSONL
events file.  This DB is provided for quick CLI queries and deduplication
checks (e.g. "was this message already sent to this contact today?").
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DDL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    started_at  TEXT NOT NULL,
    contact     TEXT,
    goal        TEXT,
    exit_code   INTEGER,
    run_dir     TEXT
);

CREATE TABLE IF NOT EXISTS sent_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    contact     TEXT NOT NULL,
    text        TEXT NOT NULL,
    sent_at     TEXT NOT NULL,
    verified    INTEGER NOT NULL DEFAULT 0
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunDB:
    def __init__(self, db_path: str) -> None:
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(DDL)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Runs
    # ------------------------------------------------------------------

    def start_run(self, run_id: str, *, contact: str | None = None, goal: str | None = None, run_dir: str | None = None) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO runs (run_id, started_at, contact, goal, run_dir) VALUES (?,?,?,?,?)",
            (run_id, _now_iso(), contact, goal, run_dir),
        )
        self._conn.commit()

    def finish_run(self, run_id: str, exit_code: int) -> None:
        self._conn.execute("UPDATE runs SET exit_code=? WHERE run_id=?", (exit_code, run_id))
        self._conn.commit()

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def record_sent(self, run_id: str, contact: str, text: str, *, verified: bool = False) -> None:
        self._conn.execute(
            "INSERT INTO sent_messages (run_id, contact, text, sent_at, verified) VALUES (?,?,?,?,?)",
            (run_id, contact, text, _now_iso(), int(verified)),
        )
        self._conn.commit()

    def was_sent_recently(self, contact: str, text: str, *, within_seconds: float = 300.0) -> bool:
        """Return True if an identical message was sent to *contact* in the last N seconds."""
        row = self._conn.execute(
            """
            SELECT sent_at FROM sent_messages
            WHERE contact = ? AND text = ?
            ORDER BY id DESC LIMIT 1
            """,
            (contact, text),
        ).fetchone()
        if row is None:
            return False
        try:
            sent_at = datetime.fromisoformat(row[0])
            now = datetime.now(timezone.utc)
            delta = (now - sent_at).total_seconds()
            return delta < within_seconds
        except Exception:
            return False

    def close(self) -> None:
        self._conn.close()
