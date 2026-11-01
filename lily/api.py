"""API REST (FastAPI). Cada visitante é isolado pelo cabeçalho `X-Session-Id`.

Documentação interativa em /docs (Swagger) e /redoc quando o servidor está rodando.
A chave do Gemini NUNCA trafega pela API: vem do ambiente do servidor.
Execução: `uvicorn lily.api:create_app --factory --reload`.
"""

from __future__ import annotations

import re

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse

from . import __version__
from . import schemas as s
from .errors import LilyError
from .logging_utils import setup_logging
from .rag import guard
from .runtime import Runtime

_SESSION_RX = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def create_app(runtime: Runtime | None = None) -> FastAPI:
    setup_logging()
    rt = runtime or Runtime()
    app = FastAPI(title="Lily Tasks API", version=__version__,
                  description="Assistente de produtividade com IA: tarefas, lembretes, e-mails (rascunho) e RAG.")  # fmt: skip
    app.state.runtime = rt

    @app.exception_handler(LilyError)
    async def _lily_error(_: Request, exc: LilyError):
        return JSONResponse(status_code=exc.status, content=exc.to_dict())

    def session(x_session_id: str = Header(..., description="ID da sessão (use POST /sessions).")) -> str:
        if not _SESSION_RX.match(x_session_id):
            raise LilyError("invalid_session", "X-Session-Id inválido (16–64 caracteres: letras, números, _ ou -).", status=422)
        return x_session_id

    # ---- infraestrutura -----------------------------------------------------------------
    @app.get("/health", tags=["infra"])
    def health():
        return {"status": "ok", "version": __version__, "mode": rt.mode_for(None), "model": rt.settings.gemini_model if rt.mode_for(None) == "real" else None}  # fmt: skip

    @app.post("/sessions", status_code=201, tags=["infra"])
    def create_session():
        sid = rt.new_session_id()
        with rt.db.tx() as c:
            rt.db.touch_session(c, sid)
        return {"session_id": sid}

    @app.put("/session/timezone", tags=["infra"])
    def set_timezone(body: s.TimezoneBody, sid: str = Depends(session)):
        from zoneinfo import ZoneInfo

        try:
            ZoneInfo(body.timezone)
        except Exception as exc:  # noqa: BLE001
            raise LilyError("invalid_timezone", "Fuso horário desconhecido (ex.: America/Sao_Paulo).", status=422) from exc
        rt.db.set_timezone(sid, body.timezone)
        return {"timezone": body.timezone}

    @app.delete("/session", status_code=204, tags=["infra"])
    def delete_session(sid: str = Depends(session)):
        rt.db.delete_session(sid)

    # ---- chat ---------------------------------------------------------------------------
    def _chat_out(r) -> s.ChatResponse:
        return s.ChatResponse(
            reply=r.reply, mode=r.mode, error=r.error,
            tool_events=[s.ToolEventOut(**e) for e in r.tool_events],
            pending_action=s.PendingOut(**r.pending) if r.pending else None,
        )  # fmt: skip

    @app.post("/chat", response_model=s.ChatResponse, tags=["chat"])
    def chat(body: s.ChatRequest, sid: str = Depends(session)):
        return _chat_out(rt.agent.chat(sid, body.message, rt.llm_for(None)))

    @app.post("/actions/{token}/confirm", response_model=s.ChatResponse, tags=["chat"])
    def confirm_action(token: str, sid: str = Depends(session)):
        return _chat_out(rt.agent.confirm(sid, token, rt.llm_for(None)))

    @app.post("/actions/{token}/cancel", response_model=s.ChatResponse, tags=["chat"])
    def cancel_action(token: str, sid: str = Depends(session)):
        return _chat_out(rt.agent.cancel(sid, token, rt.llm_for(None)))

    @app.get("/history", tags=["chat"])
    def history(limit: int = 50, sid: str = Depends(session)):
        return {"messages": rt.db.get_messages(sid, min(max(limit, 1), 200))}

    @app.get("/activity", tags=["chat"])
    def activity(sid: str = Depends(session)):
        return {"tool_log": rt.db.recent_tool_logs(sid)}

    # ---- tarefas ------------------------------------------------------------------------
    @app.get("/tasks", tags=["tarefas"])
    def list_tasks(status: str = "pendente", priority: str | None = None, due_before: str | None = None,
                   q: str | None = None, sid: str = Depends(session)):  # fmt: skip
        return {"tasks": rt.tasks.list(sid, status=status, priority=priority, due_before=due_before, query=q)}

    @app.post("/tasks", status_code=201, tags=["tarefas"])
    def create_task(body: s.TaskCreate, sid: str = Depends(session)):
        return rt.tasks.create(sid, body.title, due=body.due, priority=body.priority, notes=body.notes)

    @app.patch("/tasks/{ref}", tags=["tarefas"])
    def patch_task(ref: str, body: s.TaskPatch, sid: str = Depends(session)):
        return rt.tasks.update(sid, ref, title=body.title, due=body.due, priority=body.priority,
                               notes=body.notes, clear_due=body.clear_due)  # fmt: skip

    @app.post("/tasks/{ref}/complete", tags=["tarefas"])
    def complete_task(ref: str, sid: str = Depends(session)):
        return rt.tasks.complete(sid, ref)

    @app.delete("/tasks/{ref}", tags=["tarefas"])
    def delete_task(ref: str, confirm: bool = False, sid: str = Depends(session)):
        if not confirm:
            t = rt.tasks.resolve(sid, ref)
            raise LilyError("confirmation_required", f"Para excluir a tarefa #{t['seq']} envie ?confirm=true.", status=428)
        return rt.tasks.delete(sid, ref)

    # ---- lembretes ----------------------------------------------------------------------
    @app.get("/reminders", tags=["lembretes"])
    def list_reminders(only_pending: bool = False, sid: str = Depends(session)):
        return {"reminders": rt.reminders.list(sid, only_pending=only_pending)}

    @app.post("/reminders", status_code=201, tags=["lembretes"])
    def create_reminder(body: s.ReminderCreate, sid: str = Depends(session)):
        return rt.reminders.create(sid, body.text, body.when)

    @app.patch("/reminders/{ref}", tags=["lembretes"])
    def patch_reminder(ref: str, body: s.ReminderPatch, sid: str = Depends(session)):
        return rt.reminders.update(sid, ref, text=body.text, when=body.when)

    @app.delete("/reminders/{ref}", tags=["lembretes"])
    def delete_reminder(ref: str, confirm: bool = False, sid: str = Depends(session)):
        if not confirm:
            r = rt.reminders.resolve(sid, ref)
            raise LilyError("confirmation_required", f"Para excluir o lembrete #{r['seq']} envie ?confirm=true.", status=428)
        return rt.reminders.delete(sid, ref)

    @app.get("/notifications/due", tags=["lembretes"])
    def due_notifications(sid: str = Depends(session)):
        """Lembretes vencidos e AINDA NÃO notificados. Consultar não marca como notificado."""
        return {"due": rt.reminders.due_unnotified(sid)}

    @app.post("/notifications/{ref}/ack", tags=["lembretes"])
    def ack_notification(ref: str, sid: str = Depends(session)):
        """O cliente chama isto DEPOIS de exibir o aviso ao usuário (entrega in-app real)."""
        return rt.reminders.mark_notified(sid, ref, "in_app")

    # ---- e-mails (rascunhos; não há envio) ------------------------------------------------
    @app.get("/drafts", tags=["e-mails"])
    def list_drafts(sid: str = Depends(session)):
        return {"drafts": rt.emails.list(sid)}

    @app.patch("/drafts/{seq}", tags=["e-mails"])
    def patch_draft(seq: int, body: s.DraftPatch, sid: str = Depends(session)):
        return rt.emails.update(sid, seq, subject=body.subject, body=body.body)

    # ---- RAG ----------------------------------------------------------------------------
    @app.post("/rag/search", tags=["rag"])
    def rag_search(body: s.RagQuery):
        res = rt.index.search(body.query)
        out = []
        for p in res.passages:
            clean, flags = guard.sanitize(p.chunk.text)
            out.append({"source": p.chunk.source, "score": p.score, "text": clean, "security_flags": flags})
        return {"sufficient": res.sufficient, "coverage": res.coverage, "reason": res.reason,
                "passages": out if res.sufficient else []}  # fmt: skip

    return app

