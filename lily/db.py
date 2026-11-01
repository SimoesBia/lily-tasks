"""Persistência SQLite. Toda linha pertence a uma sessão (isolamento entre visitantes)."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

SESSION_TABLES = ("tasks", "reminders", "drafts", "messages", "tool_log", "pending_actions")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, created_at TEXT NOT NULL, last_seen TEXT NOT NULL, timezone TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
  session_id TEXT NOT NULL, seq INTEGER NOT NULL, title TEXT NOT NULL, notes TEXT,
  priority TEXT NOT NULL DEFAULT 'media', due_at TEXT, status TEXT NOT NULL DEFAULT 'pendente',
  created_at TEXT NOT NULL, completed_at TEXT, PRIMARY KEY (session_id, seq)
);
CREATE TABLE IF NOT EXISTS reminders (
  session_id TEXT NOT NULL, seq INTEGER NOT NULL, text TEXT NOT NULL, due_at TEXT NOT NULL,
  created_at TEXT NOT NULL, notified_at TEXT, notified_via TEXT, PRIMARY KEY (session_id, seq)
);
CREATE TABLE IF NOT EXISTS drafts (
  session_id TEXT NOT NULL, seq INTEGER NOT NULL, recipient TEXT, purpose TEXT NOT NULL,
  tone TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, generated_by TEXT NOT NULL,
  created_at TEXT NOT NULL, PRIMARY KEY (session_id, seq)
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL,
  content TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tool_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, tool TEXT NOT NULL,
  status TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pending_actions (
  token TEXT PRIMARY KEY, session_id TEXT NOT NULL, tool TEXT NOT NULL, args_json TEXT NOT NULL,
  summary TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        self._shared: sqlite3.Connection | None = None
        if self.path == ":memory:":
            self._shared = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
            self._shared.row_factory = sqlite3.Row
        else:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            conn.executescript(SCHEMA)
        finally:
            self._release(conn)

    def _connect(self) -> sqlite3.Connection:
        if self._shared is not None:
            return self._shared
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _release(self, conn: sqlite3.Connection) -> None:
        if self._shared is None:
            conn.close()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = self._connect()
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            finally:
                self._release(conn)

    # ---- sessões -----------------------------------------------------------------------
    def touch_session(self, conn: sqlite3.Connection, session_id: str) -> None:
        now = utcnow_iso()
        conn.execute(
            "INSERT INTO sessions (id, created_at, last_seen) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET last_seen = excluded.last_seen",
            (session_id, now, now),
        )

    def get_timezone(self, session_id: str) -> str | None:
        with self.tx() as c:
            row = c.execute("SELECT timezone FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return row["timezone"] if row else None

    def set_timezone(self, session_id: str, tz_name: str) -> None:
        with self.tx() as c:
            self.touch_session(c, session_id)
            c.execute("UPDATE sessions SET timezone = ? WHERE id = ?", (tz_name, session_id))

    def next_seq(self, conn: sqlite3.Connection, table: str, session_id: str) -> int:
        assert table in ("tasks", "reminders", "drafts")
        row = conn.execute(
            f"SELECT COALESCE(MAX(seq), 0) + 1 AS n FROM {table} WHERE session_id = ?",  # noqa: S608
            (session_id,),
        ).fetchone()
        return int(row["n"])

    def count(self, conn: sqlite3.Connection, table: str, session_id: str) -> int:
        assert table in ("tasks", "reminders", "drafts")
        row = conn.execute(
            f"SELECT COUNT(*) AS n FROM {table} WHERE session_id = ?",  # noqa: S608
            (session_id,),
        ).fetchone()
        return int(row["n"])

    def purge_stale(self, ttl_hours: int) -> int:
        """Apaga sessões inativas (e todos os seus dados). Retorna quantas sessões removeu."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        with self.tx() as c:
            ids = [r["id"] for r in c.execute("SELECT id FROM sessions WHERE last_seen < ?", (cutoff,))]
            for sid in ids:
                for table in SESSION_TABLES:
                    c.execute(f"DELETE FROM {table} WHERE session_id = ?", (sid,))  # noqa: S608
                c.execute("DELETE FROM sessions WHERE id = ?", (sid,))
        return len(ids)

    def delete_session(self, session_id: str) -> None:
        with self.tx() as c:
            for table in SESSION_TABLES:
                c.execute(f"DELETE FROM {table} WHERE session_id = ?", (session_id,))  # noqa: S608
            c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    # ---- histórico, log de ferramentas e ações pendentes --------------------------------
    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self.tx() as c:
            self.touch_session(c, session_id)
            c.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
                (session_id, role, content, utcnow_iso()),
            )

    def get_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        with self.tx() as c:
            rows = c.execute(
                "SELECT role, content, created_at FROM messages WHERE session_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def log_tool(self, session_id: str, tool: str, status: str, detail: str = "") -> None:
        """Registra só metadados (nunca o conteúdo digitado pelo usuário)."""
        with self.tx() as c:
            self.touch_session(c, session_id)
            c.execute(
                "INSERT INTO tool_log (session_id, tool, status, detail, created_at) "
                "VALUES (?,?,?,?,?)",
                (session_id, tool, status, detail[:200], utcnow_iso()),
            )

    def recent_tool_logs(self, session_id: str, limit: int = 20) -> list[dict]:
        with self.tx() as c:
            rows = c.execute(
                "SELECT tool, status, detail, created_at FROM tool_log WHERE session_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def put_pending(self, token: str, session_id: str, tool: str, args_json: str, summary: str):
        with self.tx() as c:
            self.touch_session(c, session_id)
            c.execute(
                "INSERT INTO pending_actions VALUES (?,?,?,?,?,?)",
                (token, session_id, tool, args_json, summary, utcnow_iso()),
            )

    def take_pending(self, session_id: str, token: str, max_age_min: int = 10) -> dict | None:
        """Retira (remove) uma ação pendente se ela pertence à sessão e não expirou."""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=max_age_min)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        with self.tx() as c:
            row = c.execute(
                "SELECT * FROM pending_actions WHERE token = ? AND session_id = ?",
                (token, session_id),
            ).fetchone()
            if not row:
                return None
            c.execute("DELETE FROM pending_actions WHERE token = ?", (token,))
        return dict(row) if row["created_at"] >= cutoff else None
