"""Rascunhos de e-mail. Este módulo NUNCA envia e-mails: apenas gera e guarda texto editável."""

from __future__ import annotations

from ..db import utcnow_iso
from ..errors import LilyError
from .base import BaseService

PURPOSES = (
    "follow_up", "request", "meeting", "thanks", "apology", "status_update", "introduction",
)  # fmt: skip
TONES = ("formal", "friendly", "neutral", "direct")

_GREETING = {
    "formal": "Prezado(a) {r},",
    "friendly": "Oi, {r}!",
    "neutral": "Olá, {r},",
    "direct": "{r},",
}
_CLOSING = {
    "formal": "Atenciosamente,",
    "friendly": "Um abraço,",
    "neutral": "Cordialmente,",
    "direct": "Obrigado(a),",
}
# (assunto, abertura, pedido final) — {t} é o tema
_PURPOSE = {
    "follow_up": (
        "Acompanhamento: {t}",
        "Estou entrando em contato para acompanhar {t}.",
        "Poderia me atualizar sobre o andamento?",
    ),
    "request": (
        "Solicitação: {t}",
        "Escrevo para solicitar apoio sobre {t}.",
        "Fico no aguardo do seu retorno.",
    ),
    "meeting": (
        "Proposta de reunião: {t}",
        "Gostaria de agendar uma conversa sobre {t}.",
        "Quais horários funcionam melhor para você?",
    ),
    "thanks": (
        "Obrigado(a) — {t}",
        "Quero agradecer pelo apoio durante {t}.",
        "Foi fundamental e muito apreciado.",
    ),
    "apology": (
        "Sobre {t}",
        "Peço desculpas pelo ocorrido durante {t}.",
        "Estou à disposição para corrigir o que for necessário.",
    ),
    "status_update": (
        "Atualização: {t}",
        "Segue uma atualização sobre {t}.",
        "Se tiver dúvidas ou sugestões, me avise.",
    ),
    "introduction": (
        "Apresentação: {t}",
        "Meu nome é {sender} e gostaria de me apresentar. Assunto: {t}.",
        "Ficarei feliz em conversar quando for conveniente.",
    ),
}


def render_template(
    recipient: str | None,
    purpose: str,
    tone: str,
    key_points: list[str] | None = None,
    sender: str = "[seu nome]",
) -> tuple[str, str]:
    """Gera (assunto, corpo) de forma determinística, sem LLM."""
    points = [p.strip() for p in (key_points or []) if p.strip()]
    topic = points[0] if points else "nossa última conversa"
    subject_t, intro, ask = _PURPOSE[purpose]
    fmt = {"t": topic, "sender": sender}
    greeting = _GREETING[tone].format(r=(recipient or "").strip() or "tudo bem")
    lines = [greeting, "", intro.format(**fmt)]
    if len(points) > 1:
        lines += ["", "Pontos principais:"] + [f"- {p}" for p in points[1:]]
    lines += ["", ask, "", _CLOSING[tone], sender]
    return subject_t.format(**fmt), "\n".join(lines)


class EmailService(BaseService):
    def create(
        self, sid, *, recipient, purpose, tone, subject, body, generated_by="template"
    ) -> dict:
        if purpose not in PURPOSES:
            raise LilyError("invalid_arguments", f"Finalidade inválida. Use: {', '.join(PURPOSES)}.")
        if tone not in TONES:
            raise LilyError("invalid_arguments", f"Tom inválido. Use: {', '.join(TONES)}.")
        if not subject.strip() or not body.strip():
            raise LilyError("invalid_arguments", "Assunto e corpo não podem ficar vazios.")
        with self.db.tx() as c:
            self.db.touch_session(c, sid)
            if self.db.count(c, "drafts", sid) >= self.max_items:
                raise LilyError("limit_reached", "Limite de rascunhos da sessão atingido.", status=409)
            seq = self.db.next_seq(c, "drafts", sid)
            c.execute(
                "INSERT INTO drafts (session_id, seq, recipient, purpose, tone, subject, body, "
                "generated_by, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (sid, seq, recipient, purpose, tone, subject[:200], body[:5000], generated_by,
                 utcnow_iso()),
            )  # fmt: skip
            row = c.execute(
                "SELECT * FROM drafts WHERE session_id=? AND seq=?", (sid, seq)
            ).fetchone()
        return {k: v for k, v in dict(row).items() if k != "session_id"}

    def list(self, sid: str) -> list[dict]:
        with self.db.tx() as c:
            rows = c.execute(
                "SELECT * FROM drafts WHERE session_id=? ORDER BY seq DESC", (sid,)
            ).fetchall()
        return [{k: v for k, v in dict(r).items() if k != "session_id"} for r in rows]

    def update(self, sid: str, seq: int, *, subject: str, body: str) -> dict:
        """Salva a edição manual feita pelo usuário no rascunho."""
        if not subject.strip() or not body.strip():
            raise LilyError("invalid_arguments", "Assunto e corpo não podem ficar vazios.")
        with self.db.tx() as c:
            cur = c.execute(
                "UPDATE drafts SET subject=?, body=? WHERE session_id=? AND seq=?",
                (subject[:200], body[:5000], sid, seq),
            )
            if cur.rowcount == 0:
                raise LilyError("not_found", f"O rascunho #{seq} não existe.", status=404)
            row = c.execute(
                "SELECT * FROM drafts WHERE session_id=? AND seq=?", (sid, seq)
            ).fetchone()
        return {k: v for k, v in dict(row).items() if k != "session_id"}
