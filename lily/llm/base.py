"""Interface neutra de LLM: o agente não conhece o SDK do Gemini (facilita testar e trocar)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    name: str
    args: dict = field(default_factory=dict)


@dataclass
class LLMTurn:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None  # conteúdo original do provedor (preserva, p.ex., thought signatures)


class LLMError(Exception):
    """kind: rate_limit | timeout | unavailable | auth | bad_request | blocked | bad_output | unknown"""

    def __init__(self, kind: str, message: str = "", *, retryable: bool = False,
                 retry_after: float | None = None) -> None:  # fmt: skip
        super().__init__(message or kind)
        self.kind = kind
        self.retryable = retryable
        self.retry_after = retry_after


class LLMClient(Protocol):
    def generate(self, system: str, messages: list[dict], tools: list[dict]) -> LLMTurn: ...

    def generate_structured(self, prompt: str, schema: type) -> Any: ...
