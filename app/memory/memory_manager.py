"""
MemoryManager — long-term research history via SQLite.

Stores:
  - research_history: each completed research session
  - Supports save, load, list, search operations

Schema:
  CREATE TABLE research_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      topic TEXT NOT NULL,
      plan TEXT,           -- JSON: list of research steps
      notes TEXT,          -- JSON: list of research findings per step
      report TEXT,         -- final markdown report
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages persistent research history in SQLite."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or self._default_db_path()
        self._ensure_db()

    @staticmethod
    def _default_db_path() -> str:
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        return os.path.join(project_root, "research_history.db")

    # ── Database initialization ──────────────────────────────

    def _ensure_db(self) -> None:
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    plan TEXT,
                    notes TEXT,
                    report TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        logger.info("MemoryManager initialized: %s", self.db_path)

    # ── CRUD operations ──────────────────────────────────────

    def save_research(
        self,
        topic: str,
        plan: list[dict[str, Any]] | None = None,
        notes: list[dict[str, Any]] | None = None,
        report: str | None = None,
    ) -> int:
        """
        Save a completed research session.

        Returns the new row id.
        """
        plan_json = json.dumps(plan, ensure_ascii=False) if plan else None
        notes_json = json.dumps(notes, ensure_ascii=False) if notes else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO research_history (topic, plan, notes, report)
                   VALUES (?, ?, ?, ?)""",
                (topic, plan_json, notes_json, report),
            )
            conn.commit()
            row_id = cursor.lastrowid
            logger.info("Research saved [id=%d]: %s", row_id, topic)
            return row_id

    def get_research(self, research_id: int) -> dict[str, Any] | None:
        """Retrieve a specific research session by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM research_history WHERE id = ?", (research_id,)
            ).fetchone()

        if not row:
            return None

        return self._row_to_dict(row)

    def list_research(
        self, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List recent research sessions (summary only)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, topic, created_at,
                           LENGTH(report) as report_length
                    FROM research_history
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()

        return [dict(r) for r in rows]

    def search_by_topic(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search research history by topic keyword."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, topic, created_at
                    FROM research_history
                    WHERE topic LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?""",
                (f"%{keyword}%", limit),
            ).fetchall()

        return [dict(r) for r in rows]

    def delete_research(self, research_id: int) -> bool:
        """Delete a research session by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM research_history WHERE id = ?", (research_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info("Research deleted [id=%d]", research_id)
            return deleted

    def get_count(self) -> int:
        """Return total number of saved research sessions."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM research_history"
            ).fetchone()
            return row[0] if row else 0

    # ── Enhanced: use history to augment new research ─────────

    def get_relevant_history(self, topic: str, limit: int = 3) -> list[dict[str, Any]]:
        """
        Find historically related research to enhance current session.

        Simple keyword-based relevance search.
        """
        keywords = topic.split()
        results = []
        seen_ids: set[int] = set()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for word in keywords:
                if len(word) < 2:
                    continue
                rows = conn.execute(
                    """SELECT id, topic, created_at, report
                        FROM research_history
                        WHERE topic LIKE ?
                        ORDER BY created_at DESC
                        LIMIT ?""",
                    (f"%{word}%", limit),
                ).fetchall()
                for row in rows:
                    rid = row["id"]
                    if rid not in seen_ids:
                        seen_ids.add(rid)
                        d = dict(row)
                        # Truncate report for context
                        if d.get("report"):
                            d["report"] = d["report"][:500]
                        results.append(d)

        return results[:limit]

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        for field in ("plan", "notes"):
            if d.get(field) and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except json.JSONDecodeError:
                    pass
        return d
