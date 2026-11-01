from __future__ import annotations

from ..dates import resolve_when, to_utc_iso
from ..db import utcnow_iso
from ..errors import LilyError
from ..text import fold
from .base import BaseService

PRIORITIES = ("baixa", "media", "alta")
_RANK = {"alta": 0, "media": 1, "baixa": 2}
_ALIASES = {"normal": "media", "medio": "media", "urgente": "alta", "importante": "alta"}


def normalize_priority(value: str | None) -> str:
    p = fold(value or "media").strip()
    p = _ALIASES.get(p, p)
    if p not in PRIORITIES:
        raise LilyError("invalid_arguments", "Prioridade deve ser baixa, média ou alta.")
    return p


class TaskService(BaseService):
    def _all(self, c, sid: str) -> list[dict]:
        rows = c.execute("SELECT * FROM tasks WHERE session_id = ? ORDER BY seq", (sid,)).fetchall()
        return [dict(r) for r in rows]

    def _decorate(self, row: dict) -> dict:
        row = {k: v for k, v in row.items() if k != "session_id"}
        row["overdue"] = bool(
            row["status"] == "pendente" and row["due_at"] and row["due_at"] < to_utc_iso(self.now())
        )
        return row

    def create(self, sid: str, title: str, *, due=None, priority="media", notes=None) -> dict:
        title = (title or "").strip()
        if not title:
            raise LilyError("invalid_arguments", "A tarefa precisa de um título.")
        prio = normalize_priority(priority)
        due_at = to_utc_iso(resolve_when(due, self.now(), self.tz(sid))) if due else None
        with self.db.tx() as c:
            self.db.touch_session(c, sid)
            if self.db.count(c, "tasks", sid) >= self.max_items:
                raise LilyError("limit_reached", "Limite de tarefas da sessão atingido.", status=409)
            seq = self.db.next_seq(c, "tasks", sid)
            c.execute(
                "INSERT INTO tasks (session_id, seq, title, notes, priority, due_at, status, "
                "created_at) VALUES (?,?,?,?,?,?,?,?)",
                (sid, seq, title[:200], notes, prio, due_at, "pendente", utcnow_iso()),
            )
            row = c.execute("SELECT * FROM tasks WHERE session_id=? AND seq=?", (sid, seq)).fetchone()
        return self._decorate(dict(row))

    def list(self, sid, *, status="pendente", priority=None, due_before=None, query=None):
        if status not in ("pendente", "concluida", "todas"):
            raise LilyError("invalid_arguments", "status deve ser pendente, concluida ou todas.")
        limit_iso = None
        if due_before:
            limit_iso = to_utc_iso(resolve_when(due_before, self.now(), self.tz(sid)))
        with self.db.tx() as c:
            rows = self._all(c, sid)
        if status != "todas":
            rows = [r for r in rows if r["status"] == status]
        if priority:
            rows = [r for r in rows if r["priority"] == normalize_priority(priority)]
        if limit_iso:
            rows = [r for r in rows if r["due_at"] and r["due_at"] <= limit_iso]
        if query:
            rows = [r for r in rows if fold(query) in fold(r["title"] + " " + (r["notes"] or ""))]
        rows.sort(key=lambda r: (r["due_at"] is None, r["due_at"] or "", _RANK[r["priority"]], r["seq"]))
        return [self._decorate(r) for r in rows]

    def resolve(self, sid: str, ref: str) -> dict:
        with self.db.tx() as c:
            rows = self._all(c, sid)
        return self.find_by_ref(rows, ref, "title", "tarefa")

    def update(self, sid, ref, *, title=None, due=None, priority=None, notes=None, clear_due=False):
        if title is None and due is None and priority is None and notes is None and not clear_due:
            raise LilyError("invalid_arguments", "Nada para alterar: informe ao menos um campo.")
        target = self.resolve(sid, ref)
        fields: dict = {}
        if title is not None:
            if not title.strip():
                raise LilyError("invalid_arguments", "O título não pode ficar vazio.")
            fields["title"] = title.strip()[:200]
        if priority is not None:
            fields["priority"] = normalize_priority(priority)
        if notes is not None:
            fields["notes"] = notes
        if clear_due:
            fields["due_at"] = None
        elif due:
            fields["due_at"] = to_utc_iso(resolve_when(due, self.now(), self.tz(sid)))
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self.db.tx() as c:
            c.execute(
                f"UPDATE tasks SET {sets} WHERE session_id = ? AND seq = ?",  # noqa: S608
                (*fields.values(), sid, target["seq"]),
            )
            row = c.execute(
                "SELECT * FROM tasks WHERE session_id=? AND seq=?", (sid, target["seq"])
            ).fetchone()
        return self._decorate(dict(row))

    def complete(self, sid: str, ref: str) -> dict:
        target = self.resolve(sid, ref)
        if target["status"] == "concluida":
            raise LilyError("already_done", f"A tarefa #{target['seq']} já estava concluída.", status=409)
        with self.db.tx() as c:
            c.execute(
                "UPDATE tasks SET status='concluida', completed_at=? WHERE session_id=? AND seq=?",
                (utcnow_iso(), sid, target["seq"]),
            )
            row = c.execute(
                "SELECT * FROM tasks WHERE session_id=? AND seq=?", (sid, target["seq"])
            ).fetchone()
        return self._decorate(dict(row))

    def delete(self, sid: str, ref: str) -> dict:
        target = self.resolve(sid, ref)
        with self.db.tx() as c:
            c.execute("DELETE FROM tasks WHERE session_id=? AND seq=?", (sid, target["seq"]))
        return self._decorate(target)
