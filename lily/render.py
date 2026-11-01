"""Renderização HTML dos painéis (funções puras; todo texto do usuário é escapado)."""

from __future__ import annotations

import html
from zoneinfo import ZoneInfo

from .dates import format_local, from_utc_iso

_PRIO = {"alta": "alta", "media": "média", "baixa": "baixa"}
_STATE = {
    "registrado": ("registrado", "chip-reg", "Registrado. O horário ainda não chegou."),
    "vencido_sem_notificacao": ("vencido · não notificado", "chip-due", "O horário passou e nenhum aviso foi entregue."),
    "notificado": ("notificado", "chip-ok", "Aviso exibido neste app."),
}  # fmt: skip


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def _empty(msg: str) -> str:
    return f'<div class="lily-empty">{esc(msg)}</div>'


def render_tasks(tasks: list[dict], tz: ZoneInfo) -> str:
    if not tasks:
        return _empty("Nenhuma tarefa aqui. Peça à Lily: “Crie uma tarefa para enviar o relatório amanhã às 9h”.")
    rows = []
    for t in tasks:
        done = " done" if t["status"] == "concluida" else ""
        late = " late" if t.get("overdue") else ""
        due = esc(format_local(t["due_at"], tz))
        extra = " · atrasada" if t.get("overdue") else ""
        rows.append(
            f'<div class="lily-row prio-{esc(t["priority"])}{done}">'
            f'<div class="lily-main"><span class="lily-title">{esc(t["title"])}</span>'
            f'<span class="lily-meta">#{t["seq"]} · prioridade {_PRIO[t["priority"]]}'
            f'{" · concluída" if done else ""}</span></div>'
            f'<div class="lily-due{late}">{due}{extra}</div></div>'
        )
    return '<div class="lily-list">' + "".join(rows) + "</div>"


def render_reminders(reminders: list[dict], tz: ZoneInfo) -> str:
    note = (
        '<div class="lily-note">Lembretes só avisam <b>enquanto este app está aberto</b>. '
        "Não há envio por e-mail, push ou WhatsApp.</div>"
    )
    if not reminders:
        return note + _empty("Nenhum lembrete. Experimente: “Me lembre de ligar para a Ana sexta às 14h”.")
    rows = []
    for r in reminders:
        label, css, hint = _STATE[r["state"]]
        when = esc(format_local(r["due_at"], tz))
        sent = ""
        if r["notified_at"]:
            sent = f' às {from_utc_iso(r["notified_at"]).astimezone(tz):%H:%M}'
        rows.append(
            f'<div class="lily-row"><div class="lily-main"><span class="lily-title">{esc(r["text"])}</span>'
            f'<span class="lily-meta">#{r["seq"]} · {when}</span></div>'
            f'<div><span class="lily-chip {css}" title="{esc(hint)}">{esc(label)}{esc(sent)}</span></div></div>'
        )
    return note + '<div class="lily-list">' + "".join(rows) + "</div>"


def render_activity(logs: list[dict], tz: ZoneInfo) -> str:
    if not logs:
        return _empty("Nenhuma ferramenta executada ainda nesta sessão.")
    rows = []
    for e in logs:
        ok = e["status"] == "ok"
        css = "chip-ok" if ok else ("chip-reg" if "pending" in e["status"] or e["status"] == "cancelled" else "chip-due")
        when = from_utc_iso(e["created_at"]).astimezone(tz)
        rows.append(
            f'<div class="lily-row"><div class="lily-main"><span class="lily-title mono">{esc(e["tool"])}</span>'
            f'<span class="lily-meta">{when:%H:%M:%S}</span></div>'
            f'<div><span class="lily-chip {css}">{esc(e["status"])}</span></div></div>'
        )
    return '<div class="lily-list">' + "".join(rows) + "</div>"


def mode_badge(mode: str, model: str) -> str:
    if mode == "real":
        return f'<span class="lily-badge real">IA real · Gemini ({esc(model)})</span>'
    return '<span class="lily-badge demo">Demonstração simulada · regras fixas, sem LLM</span>'


def header(mode: str, model: str, public: bool) -> str:
    scope = "Dados isolados por visitante e apagados após inatividade." if public else "Dados salvos localmente (SQLite)."
    return (
        '<div class="lily-header"><div><span class="lily-brand">Lily Tasks</span>'
        '<span class="lily-tag">assistente de produtividade</span></div>'
        f'<div class="lily-hright">{mode_badge(mode, model)}<span class="lily-scope">{esc(scope)}</span></div></div>'
    )


def events_markdown(events: list[dict]) -> str:
    if not events:
        return ""
    lines = [f"> 🔧 `{e['tool']}` · {e['status']}" for e in events]
    return "\n\n" + "\n".join(lines)
