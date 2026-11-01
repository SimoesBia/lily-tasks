"""Logs seguros: redigem chaves de API e nunca registram o texto das conversas."""

from __future__ import annotations

import logging
import re

_SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),  # chaves do Google AI Studio
    re.compile(r"(?i)(api[_-]?key|token|authorization|bearer)(\s*[=:]\s*)([^\s,;]+)"),
]


def redact(text: str) -> str:
    text = _SECRET_PATTERNS[0].sub("[REDACTED_KEY]", text)
    return _SECRET_PATTERNS[1].sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(str(record.getMessage()))
        record.args = ()
        return True


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if any(isinstance(f, RedactingFilter) for h in root.handlers for f in h.filters):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactingFilter())
    root.addHandler(handler)
    root.setLevel(level)
