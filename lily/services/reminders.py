"""Lembretes.

Estados (nunca simulados):
- registrado: existe no banco e o horário ainda não chegou;
- vencido_sem_notificacao: horário passou e NENHUM canal confirmou a entrega;
- notificado: um canal real confirmou a entrega (hoje, apenas o canal in-app da interface).
"""

from __future__ import annotations

from ..dates import resolve_when, to_utc_iso
from ..db import utcnow_iso
from ..errors import LilyError
from .base import BaseService


class ReminderService(BaseService):
    def _all(self, c, sid: str) -> list[dict]:
        rows = c.execute(
            "SELECT * FROM reminders WHERE session_id = ? ORDER BY seq", (sid,)
        ).fetchall()
        return [dict(r) for r in rows]

    def _decorate(self, row: dict) -> dict:
        row = {k: v for k, v in row.items() if k != "session_id"}
        if row["notified_at"]:
            row["state"] = "notificado"
        elif row["due_at"] <= to_utc_iso(self.now()):
            row["state"] = "vencido_sem_notificacao"
        else:
            row["state"] = "registrado"
        return row

    def create(self, sid: str, text: str, when: str) -> dict:
        text = (text or "").strip()
        if not text:
            raise LilyError("invalid_arguments", "O lembrete precisa de um texto.")
        due = resolve_when(when, self.now(), self.tz(sid))
        if to_utc_iso(due) < to_utc_iso(self.now()):
            raise LilyError("past_date", "Esse horário já passou. Informe uma data futura.")
        with self.db.tx() as c:
            self.db.touch_session(c, sid)
            if self.db.count(c, "reminders", sid) >= self.max_items:
                raise LilyError("limit_reached", "Limite de lembretes da sessão atingido.", status=409)
            seq = self.db.next_seq(c, "reminders", sid)
            c.execute(
                "INSERT INTO reminders (session_id, seq, text, due_at, created_at) VALUES (?,?,?,?,?)",
                (sid, seq, text[:300], to_utc_iso(due), utcnow_iso()),
            )
            row = c.execute(
                "SELECT * FROM reminders WHERE session_id=? AND seq=?", (sid, seq)
            ).fetchone()
        return self._decorate(dict(row))

    def list(self, sid: str, *, only_pending: bool = False) -> list[dict]:
        with self.db.tx() as c:
            rows = [self._decorate(r) for r in self._all(c, sid)]
        if only_pending:
            rows = [r for r in rows if r["state"] != "notificado"]
        return sorted(rows, key=lambda r: (r["due_at"], r["seq"]))

    def resolve(self, sid: str, ref: str) -> dict:
        with self.db.tx() as c:
            rows = self._all(c, sid)
        return self.find_by_ref(rows, ref, "text", "lembrete")

    def update(self, sid: str, ref: str, *, text=None, when=None) -> dict:
        if text is None and when is None:
            raise LilyError("invalid_arguments", "Nada para alterar: informe texto ou horário.")
        target = self.resolve(sid, ref)
        fields: dict = {}
        if text is not None:
            if not text.strip():
                raise LilyError("invalid_arguments", "O texto não pode ficar vazio.")
            fields["text"] = text.strip()[:300]
        if when is not None:
            due = resolve_when(when, self.now(), self.tz(sid))
            if to_utc_iso(due) < to_utc_iso(self.now()):
                raise LilyError("past_date", "Esse horário já passou. Informe uma data futura.")
            fields.update(due_at=to_utc_iso(due), notified_at=None, notified_via=None)
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self.db.tx() as c:
            c.execute(
                f"UPDATE reminders SET {sets} WHERE session_id=? AND seq=?",  # noqa: S608
                (*fields.values(), sid, target["seq"]),
            )
            row = c.execute(
                "SELECT * FROM reminders WHERE session_id=? AND seq=?", (sid, target["seq"])
            ).fetchone()
        return self._decorate(dict(row))

    def delete(self, sid: str, ref: str) -> dict:
        target = self.resolve(sid, ref)
        with self.db.tx() as c:
            c.execute("DELETE FROM reminders WHERE session_id=? AND seq=?", (sid, target["seq"]))
        return self._decorate(target)

    # ---- entrega ------------------------------------------------------------------------
    def due_unnotified(self, sid: str) -> list[dict]:
        return [r for r in self.list(sid) if r["state"] == "vencido_sem_notificacao"]

    def mark_notified(self, sid: str, ref: str, via: str = "in_app") -> dict:
        """Só deve ser chamado depois que um canal REAL entregou o aviso (ex.: UI exibiu)."""
        target = self.resolve(sid, ref)
        with self.db.tx() as c:
            c.execute(
                "UPDATE reminders SET notified_at=?, notified_via=? "
                "WHERE session_id=? AND seq=? AND notified_at IS NULL",
                (utcnow_iso(), via, sid, target["seq"]),
            )
            row = c.execute(
                "SELECT * FROM reminders WHERE session_id=? AND seq=?", (sid, target["seq"])
            ).fetchone()
        return self._decorate(dict(row))
