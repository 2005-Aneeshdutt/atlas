"""
SQLite persistence layer for ATLAS sessions and attack results.

The database is auto-created at data/results.db on first call to init_db().
Schema migrations are run idempotently using try/except on ALTER TABLE so
existing databases are upgraded without data loss.
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "results.db")


def init_db():
    """Create tables if they don't exist and apply any pending schema migrations."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            target_model TEXT,
            target_provider TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attack_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            attack_id TEXT,
            category TEXT,
            name TEXT,
            severity TEXT DEFAULT 'medium',
            prompt TEXT,
            mutated_prompt TEXT,
            response TEXT,
            judge_score REAL,
            judge_reasoning TEXT,
            violation_type TEXT,
            is_successful INTEGER,
            retry_count INTEGER,
            created_at TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()

    for migration in [
        "ALTER TABLE attack_results ADD COLUMN severity TEXT DEFAULT 'medium'",
        "ALTER TABLE attack_results ADD COLUMN attack_latency_ms INTEGER DEFAULT 0",
        "ALTER TABLE attack_results ADD COLUMN judge_latency_ms INTEGER DEFAULT 0",
    ]:
        try:
            conn.execute(migration)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists

    conn.close()


def save_session(session_id: str, target_model: str, target_provider: str):
    """Insert a new session row. Called once at the start of each run_session() call."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO sessions (id, target_model, target_provider, created_at) VALUES (?, ?, ?, ?)",
        (session_id, target_model, target_provider, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def save_result(session_id: str, result: dict):
    """Insert one AttackResult dict into attack_results. Called by save_result_node."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO attack_results
        (session_id, attack_id, category, name, severity, prompt, mutated_prompt, response,
         judge_score, judge_reasoning, violation_type, is_successful, retry_count,
         attack_latency_ms, judge_latency_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            result["attack_id"],
            result["category"],
            result["name"],
            result.get("severity", "medium"),
            result["prompt"],
            result.get("mutated_prompt"),
            result["response"],
            result["judge_score"],
            result["judge_reasoning"],
            result["violation_type"],
            1 if result["is_successful"] else 0,
            result["retry_count"],
            result.get("attack_latency_ms", 0),
            result.get("judge_latency_ms", 0),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_session_results(session_id: str) -> list:
    """Return all attack result rows for a single session as a list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM attack_results WHERE session_id = ?", (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_sessions() -> list:
    """Return all sessions with aggregate attack counts, ordered newest-first."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT s.*, COUNT(a.id) as total, SUM(a.is_successful) as successful "
        "FROM sessions s LEFT JOIN attack_results a ON s.id = a.session_id "
        "GROUP BY s.id ORDER BY s.created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_results() -> list:
    """Return every attack result row across all sessions, ordered newest-first."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM attack_results ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
