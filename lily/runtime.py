"""Raiz de composição: monta banco, serviços, RAG, ferramentas e agente."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from .agent import Agent
from .config import Settings
from .db import Database
from .errors import LilyError
from .rag.index import DocumentIndex
from .services import EmailService, ReminderService, TaskService
from .tools import ToolRegistry

LLMFactory = Callable[[str], object]


def _default_llm_factory(settings: Settings) -> LLMFactory:
    def make(api_key: str):
        from .llm.gemini import GeminiClient

        return GeminiClient(
            api_key,
            settings.gemini_model,
            timeout_s=settings.llm_timeout_s,
            max_retries=settings.llm_max_retries,
        )

    return make


class Runtime:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
        llm_factory: LLMFactory | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._llm_factory = llm_factory or _default_llm_factory(self.settings)
        self._env_llm = None
        self.db = Database(self.settings.db_path)
        args = (self.db, self.settings.timezone, self.clock, self.settings.max_items_per_session)
        self.tasks, self.reminders, self.emails = TaskService(*args), ReminderService(*args), EmailService(*args)
        self.index = DocumentIndex.from_dir(Path(self.settings.docs_dir))
        self.registry = ToolRegistry(self.db, self.tasks, self.reminders, self.emails, self.index)
        self.agent = Agent(self.settings, self.db, self.registry, self.clock)
        self.db.purge_stale(self.settings.session_ttl_hours)

    @staticmethod
    def new_session_id() -> str:
        return uuid.uuid4().hex

    def llm_for(self, api_key: str | None = None):
        """Chave do visitante (só em memória) > chave do servidor (se permitido) > None (demo)."""
        key = (api_key or "").strip()
        if key:
            if len(key) < 20 or any(ch.isspace() for ch in key):
                raise LilyError("invalid_key", "A chave informada não parece uma chave válida do Gemini.")
            return self._llm_factory(key)
        if self.settings.env_llm_enabled:
            if self._env_llm is None:
                self._env_llm = self._llm_factory(self.settings.gemini_api_key)  # type: ignore[arg-type]
            return self._env_llm
        return None

    def mode_for(self, api_key: str | None = None) -> str:
        return "real" if (api_key or "").strip() or self.settings.env_llm_enabled else "demo"
