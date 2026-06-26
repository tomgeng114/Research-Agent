"""
Initialize the SQLite database for Research-Agent.

Run this script to create/reset the database:
    python init_db.py

Options:
    python init_db.py          — create tables if not exist
    python init_db.py --reset  — drop and recreate all tables
"""
from __future__ import annotations

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def init_db(reset: bool = False) -> None:
    """Create (or recreate) the research_history table."""
    db_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "research_history.db"
    )

    if reset and os.path.exists(db_path):
        os.remove(db_path)
        print(f"[OK] Removed existing database: {db_path}")

    from app.memory.memory_manager import MemoryManager

    memory = MemoryManager(db_path)
    count = memory.get_count()
    print(f"[OK] Database initialized: {db_path}")
    print(f"[OK] Existing research records: {count}")
    print("[OK] Tables: research_history")


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    init_db(reset=reset)
