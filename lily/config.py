"""Configuração via variáveis de ambiente (nunca grava segredos em disco)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | None = None) -> None:
    """Carrega um .env simples (KEY=VALUE) sem sobrescrever variáveis já definidas."""
    env_file = path or ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "sim", "on"}


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-flash-latest"
    timezone: str = "America/Sao_Paulo"
    db_path: str = str(ROOT / "data" / "lily.sqlite3")
    docs_dir: str = str(ROOT / "data" / "docs")
    llm_timeout_s: float = 30.0
    llm_max_retries: int = 3
    max_tool_steps: int = 5
    max_message_chars: int = 2000
    rate_limit_per_min: int = 12
    max_items_per_session: int = 200
    session_ttl_hours: int = 6
    force_demo: bool = False
    public_space: bool = False
    allow_shared_key: bool = False

    @property
    def env_llm_enabled(self) -> bool:
        """A chave do servidor só é usada localmente (ou se o dono liberar explicitamente)."""
        if not self.gemini_api_key or self.force_demo:
            return False
        return (not self.public_space) or self.allow_shared_key

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        key = (os.getenv("GEMINI_API_KEY") or "").strip() or None
        return cls(
            gemini_api_key=key,
            gemini_model=os.getenv("GEMINI_MODEL", cls.gemini_model),
            timezone=os.getenv("LILY_TIMEZONE", cls.timezone),
            db_path=os.getenv("LILY_DB_PATH", cls.db_path),
            docs_dir=os.getenv("LILY_DOCS_DIR", cls.docs_dir),
            llm_timeout_s=_float("LILY_LLM_TIMEOUT_S", cls.llm_timeout_s),
            llm_max_retries=_int("LILY_LLM_MAX_RETRIES", cls.llm_max_retries),
            max_tool_steps=_int("LILY_MAX_TOOL_STEPS", cls.max_tool_steps),
            max_message_chars=_int("LILY_MAX_MESSAGE_CHARS", cls.max_message_chars),
            rate_limit_per_min=_int("LILY_RATE_LIMIT_PER_MIN", cls.rate_limit_per_min),
            max_items_per_session=_int("LILY_MAX_ITEMS", cls.max_items_per_session),
            session_ttl_hours=_int("LILY_SESSION_TTL_HOURS", cls.session_ttl_hours),
            force_demo=_bool("LILY_FORCE_DEMO"),
            public_space=_bool("LILY_PUBLIC") or bool(os.getenv("SPACE_ID")),
            allow_shared_key=_bool("LILY_ALLOW_SHARED_KEY"),
        )
