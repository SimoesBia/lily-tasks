import logging

from lily.llm.base import LLMError
from lily.llm.gemini import classify_exception
from lily.llm.retry import call_with_retries
from lily.logging_utils import RedactingFilter, redact


def test_redacts_api_keys():
    key = "AIza" + "x" * 35
    assert key not in redact(f"erro com {key} no header")
    assert "supersecret" not in redact("api_key=supersecret")
    rec = logging.LogRecord("t", logging.INFO, "f", 1, "chave %s", (key,), None)
    RedactingFilter().filter(rec)
    assert key not in rec.msg


def test_retries_transient_errors_with_backoff():
    calls, sleeps = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise LLMError("rate_limit", retryable=True)
        return "ok"

    assert call_with_retries(flaky, max_retries=3, sleep=sleeps.append, rng=lambda: 1.0) == "ok"
    assert len(calls) == 3 and sleeps == [1.0, 2.0]  # backoff exponencial


def test_does_not_retry_permanent_errors_and_gives_up():
    n = []

    def auth():
        n.append(1)
        raise LLMError("auth")

    try:
        call_with_retries(auth, max_retries=3, sleep=lambda s: None)
    except LLMError as e:
        assert e.kind == "auth" and len(n) == 1
    else:
        raise AssertionError

    m = []

    def always():
        m.append(1)
        raise LLMError("unavailable", retryable=True)

    try:
        call_with_retries(always, max_retries=2, sleep=lambda s: None)
    except LLMError:
        assert len(m) == 3  # 1 tentativa + 2 retries
    else:
        raise AssertionError


def test_classify_provider_exceptions():
    class E(Exception):
        def __init__(self, code):
            self.code = code

    assert classify_exception(E(429)).kind == "rate_limit" and classify_exception(E(429)).retryable
    assert classify_exception(E(503)).retryable
    assert classify_exception(E(403)).kind == "auth" and not classify_exception(E(403)).retryable
    assert classify_exception(TimeoutError()).kind == "timeout"
