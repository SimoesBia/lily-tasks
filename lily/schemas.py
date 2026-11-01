"""Modelos Pydantic: validação estrita dos argumentos de ferramentas e dos contratos da API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Priority = Literal["baixa", "media", "alta"]
Purpose = Literal[
    "follow_up", "request", "meeting", "thanks", "apology", "status_update", "introduction"
]
Tone = Literal["formal", "friendly", "neutral", "direct"]

WHEN_HELP = (
    "Data/hora em ISO 8601 (2026-11-05T09:00:00-03:00) ou frase em português "
    "('amanhã às 9h', 'sexta 14h30', 'daqui a 2 horas', 'dia 15')."
)


class Strict(BaseModel):
    """Rejeita campos desconhecidos: o LLM não consegue 'inventar' parâmetros."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---- argumentos das ferramentas -------------------------------------------------------------
class CreateTaskArgs(Strict):
    title: str = Field(min_length=1, max_length=200, description="Título curto da tarefa.")
    due: str | None = Field(default=None, max_length=80, description="Prazo. " + WHEN_HELP)
    priority: Priority = Field(default="media", description="baixa, media ou alta.")
    notes: str | None = Field(default=None, max_length=1000, description="Observações opcionais.")


class ListTasksArgs(Strict):
    status: Literal["pendente", "concluida", "todas"] = Field(
        default="pendente", description="Filtro de status."
    )
    priority: Priority | None = Field(default=None, description="Filtrar por prioridade.")
    due_before: str | None = Field(
        default=None, max_length=80, description="Só tarefas com prazo até esta data. " + WHEN_HELP
    )
    query: str | None = Field(default=None, max_length=100, description="Texto no título.")


class UpdateTaskArgs(Strict):
    task: str = Field(min_length=1, max_length=200, description="Número (ex.: '3') ou trecho do título.")
    title: str | None = Field(default=None, max_length=200)
    due: str | None = Field(default=None, max_length=80, description="Novo prazo. " + WHEN_HELP)
    clear_due: bool = Field(default=False, description="true para remover o prazo.")
    priority: Priority | None = None
    notes: str | None = Field(default=None, max_length=1000)


class TaskRefArgs(Strict):
    task: str = Field(min_length=1, max_length=200, description="Número (ex.: '3') ou trecho do título.")


class CreateReminderArgs(Strict):
    text: str = Field(min_length=1, max_length=300, description="Do que lembrar.")
    when: str = Field(min_length=1, max_length=80, description="Quando. " + WHEN_HELP)


class ListRemindersArgs(Strict):
    only_pending: bool = Field(default=False, description="true para ocultar já notificados.")


class UpdateReminderArgs(Strict):
    reminder: str = Field(min_length=1, max_length=200, description="Número ou trecho do texto.")
    text: str | None = Field(default=None, max_length=300)
    when: str | None = Field(default=None, max_length=80, description="Novo horário. " + WHEN_HELP)


class ReminderRefArgs(Strict):
    reminder: str = Field(min_length=1, max_length=200, description="Número ou trecho do texto.")


class DraftEmailArgs(Strict):
    recipient: str | None = Field(default=None, max_length=120, description="Nome do destinatário.")
    purpose: Purpose = Field(description="Finalidade do e-mail.")
    tone: Tone = Field(default="neutral", description="Tom do texto.")
    key_points: list[str] = Field(default_factory=list, max_length=8, description="Pontos a incluir.")
    subject: str | None = Field(default=None, max_length=200, description="Assunto, se já redigido.")
    body: str | None = Field(default=None, max_length=5000, description="Corpo, se já redigido.")


class SearchDocsArgs(Strict):
    query: str = Field(min_length=3, max_length=300, description="Pergunta sobre os documentos.")


class EmailContent(BaseModel):
    """Saída estruturada (structured output) usada para redigir e-mails com o LLM."""

    subject: str = Field(max_length=200)
    body: str = Field(max_length=5000)


# ---- contratos da API -----------------------------------------------------------------------
class ChatRequest(Strict):
    message: str = Field(min_length=1, max_length=4000)


class ToolEventOut(BaseModel):
    tool: str
    status: str
    summary: str


class PendingOut(BaseModel):
    token: str
    summary: str


class ChatResponse(BaseModel):
    reply: str
    mode: Literal["real", "demo"]
    tool_events: list[ToolEventOut] = []
    pending_action: PendingOut | None = None
    error: str | None = None


class TaskCreate(Strict):
    title: str = Field(min_length=1, max_length=200)
    due: str | None = Field(default=None, max_length=80)
    priority: Priority = "media"
    notes: str | None = Field(default=None, max_length=1000)


class TaskPatch(Strict):
    title: str | None = Field(default=None, max_length=200)
    due: str | None = Field(default=None, max_length=80)
    clear_due: bool = False
    priority: Priority | None = None
    notes: str | None = Field(default=None, max_length=1000)


class ReminderCreate(Strict):
    text: str = Field(min_length=1, max_length=300)
    when: str = Field(min_length=1, max_length=80)


class ReminderPatch(Strict):
    text: str | None = Field(default=None, max_length=300)
    when: str | None = Field(default=None, max_length=80)


class DraftPatch(Strict):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)


class TimezoneBody(Strict):
    timezone: str = Field(min_length=3, max_length=64)


class RagQuery(Strict):
    query: str = Field(min_length=3, max_length=300)
