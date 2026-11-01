"""Adaptador do SDK oficial `google-genai` (pip install google-genai).

- tool calling manual (automatic_function_calling desativado): quem executa é o nosso registro;
- timeout via HttpOptions; retries/backoff em erros 429/5xx/timeout;
- o conteúdo bruto do modelo é reaproveitado no histórico para preservar thought signatures.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .base import LLMError, LLMTurn, ToolCall
from .retry import call_with_retries


def classify_exception(exc: Exception) -> LLMError:
    """Mapeia exceções do SDK/HTTP para LLMError. Não depende de importar o SDK."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    name = type(exc).__name__.lower()
    if "timeout" in name or isinstance(exc, TimeoutError):
        return LLMError("timeout", "Tempo esgotado ao chamar o modelo.", retryable=True)
    if code == 429:
        return LLMError("rate_limit", "Limite de requisições atingido.", retryable=True)
    if isinstance(code, int) and code in (500, 502, 503, 504):
        return LLMError("unavailable", "Serviço do modelo indisponível.", retryable=True)
    if code in (401, 403):
        return LLMError("auth", "Chave de API recusada.")
    if code == 400:
        return LLMError("bad_request", "Requisição recusada pelo modelo.")
    if "connect" in name or "network" in name:
        return LLMError("unavailable", "Falha de rede ao chamar o modelo.", retryable=True)
    return LLMError("unknown", f"Erro inesperado do provedor ({type(exc).__name__}).")


def to_contents(messages: list[dict], types: Any) -> list:
    """Converte o histórico neutro em `Content` do Gemini (agrupa respostas de ferramentas)."""
    contents: list = []
    tool_parts: list = []

    def flush() -> None:
        if tool_parts:
            contents.append(types.Content(role="user", parts=list(tool_parts)))
            tool_parts.clear()

    for m in messages:
        role = m["role"]
        if role == "tool":
            tool_parts.append(
                types.Part.from_function_response(name=m["name"], response={"result": m["result"]})
            )
            continue
        flush()
        if role == "user":
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m["text"])]))
        elif m.get("raw") is not None:
            contents.append(m["raw"])
        else:
            parts = []
            if m.get("text"):
                parts.append(types.Part.from_text(text=m["text"]))
            for c in m.get("tool_calls", []):
                parts.append(types.Part.from_function_call(name=c["name"], args=c["args"]))
            contents.append(types.Content(role="model", parts=parts))
    flush()
    return contents


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout_s: float = 30.0,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        from google import genai  # importação tardia: o modo demo não exige o SDK
        from google.genai import types

        self._types = types
        self._model = model
        self._max_retries = max_retries
        self._sleep = sleep
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_s * 1000))
        )

    def _call(self, contents: Any, config: Any) -> Any:
        try:
            return self._client.models.generate_content(
                model=self._model, contents=contents, config=config
            )
        except Exception as exc:  # noqa: BLE001
            raise classify_exception(exc) from exc

    def generate(self, system: str, messages: list[dict], tools: list[dict]) -> LLMTurn:
        t = self._types
        config = t.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,
            tools=[t.Tool(function_declarations=tools)],
            automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True),
        )
        contents = to_contents(messages, t)
        resp = call_with_retries(
            lambda: self._call(contents, config), max_retries=self._max_retries, sleep=self._sleep
        )
        return self._parse(resp)

    @staticmethod
    def _parse(resp: Any) -> LLMTurn:
        cands = getattr(resp, "candidates", None) or []
        content = cands[0].content if cands else None
        if content is None or not getattr(content, "parts", None):
            raise LLMError("blocked", "O modelo não devolveu conteúdo (possível bloqueio de segurança).")
        text = "".join(
            p.text for p in content.parts if getattr(p, "text", None) and not getattr(p, "thought", False)
        )
        calls = [
            ToolCall(p.function_call.name, dict(p.function_call.args or {}))
            for p in content.parts
            if getattr(p, "function_call", None)
        ]
        return LLMTurn(text=text.strip(), tool_calls=calls, raw=content)

    def generate_structured(self, prompt: str, schema: type) -> Any:
        """Saída estruturada: JSON validado pelo schema Pydantic informado."""
        t = self._types
        config = t.GenerateContentConfig(
            response_mime_type="application/json", response_schema=schema, temperature=0.4
        )
        resp = call_with_retries(
            lambda: self._call(prompt, config), max_retries=self._max_retries, sleep=self._sleep
        )
        try:
            return schema.model_validate_json(resp.text)
        except Exception as exc:  # noqa: BLE001
            raise LLMError("bad_output", "O modelo não devolveu JSON válido.") from exc
