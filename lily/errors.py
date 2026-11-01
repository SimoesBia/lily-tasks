"""Erros de domínio com código estável (usados por API, ferramentas e UI)."""

from __future__ import annotations


class LilyError(Exception):
    """Erro previsível de negócio. `code` é estável e seguro para expor."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 400,
        candidates: list[dict] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.candidates = candidates or []

    def to_dict(self) -> dict:
        out: dict = {"ok": False, "error": self.code, "message": self.message}
        if self.candidates:
            out["candidates"] = self.candidates
        return out
