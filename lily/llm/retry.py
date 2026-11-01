"""Retries com backoff exponencial + jitter, só para erros transitórios."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

from .base import LLMError

T = TypeVar("T")
log = logging.getLogger("lily.llm")


def call_with_retries(
    fn: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 20.0,
    sleep: Callable[[float], None] = time.sleep,
    rng: Callable[[], float] = random.random,
) -> T:
    attempt = 0
    while True:
        try:
            return fn()
        except LLMError as exc:
            if not exc.retryable or attempt >= max_retries:
                raise
            delay = min(max_delay, base_delay * (2**attempt)) * (0.5 + rng() / 2)
            if exc.retry_after:
                delay = max(delay, min(exc.retry_after, max_delay))
            log.warning("LLM transitório (%s); nova tentativa %d em %.1fs", exc.kind, attempt + 1, delay)
            sleep(delay)
            attempt += 1
