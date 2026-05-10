"""SQLite persistence layer for API users, sessions, and messages."""

import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path


class APISessionStore:
    """Small SQLite store for multi-user session metadata."""

    def __init__(self, db_path):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with closing(self._connect()) as conn, conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    bladerunner_session_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """)

    def _now(self):
        return datetime.now(UTC).isoformat()

    def ensure_user(self, user_id):
        now = self._now()
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT OR IGNORE INTO users(id, created_at) VALUES (?, ?)",
                (user_id, now),
            )

    def create_session(self, user_id, title, bladerunner_session_id):
        self.ensure_user(user_id)
        now = self._now()
        session_id = str(uuid.uuid4())

        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO sessions(
                    id, user_id, title, bladerunner_session_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, user_id, title, bladerunner_session_id, now, now),
            )

        return {
            "id": session_id,
            "user_id": user_id,
            "title": title,
            "bladerunner_session_id": bladerunner_session_id,
            "created_at": now,
            "updated_at": now,
        }

    def get_session(self, user_id, session_id):
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()

        return dict(row) if row else None

    def list_sessions(self, user_id, limit=50):
        with closing(self._connect()) as conn, conn:
            rows = conn.execute(
                """
                SELECT * FROM sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        return [dict(row) for row in rows]

    def touch_session(self, session_id):
        now = self._now()
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )

    def add_message(self, session_id, role, content):
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO messages(session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, self._now()),
            )

    def list_messages(self, session_id, limit=200):
        with closing(self._connect()) as conn, conn:
            rows = conn.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

        return [dict(row) for row in rows]
