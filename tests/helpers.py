from __future__ import annotations

from datetime import datetime, timedelta

from lily.db import Database
from lily.errors import LilyError
from lily.services import EmailService, ReminderService, TaskService

TZ = "America/Sao_Paulo"


class FixedClock:
    """Relógio controlável: quarta 2026-11-04 10:00 em Brasília (13:00 UTC)."""

    def __init__(self, iso: str = "2026-11-04T13:00:00+00:00") -> None:
        self.t = datetime.fromisoformat(iso)

    def __call__(self) -> datetime:
        return self.t

    def advance(self, **kw) -> None:
        self.t += timedelta(**kw)


class expect_error:
    """with expect_error('not_found'): ...  (sem depender do pytest)"""

    def __init__(self, code: str) -> None:
        self.code = code

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        if et is None:
            raise AssertionError(f"esperava LilyError({self.code}), nada foi levantado")
        if not issubclass(et, LilyError):
            return False
        assert ev.code == self.code, f"esperava {self.code}, veio {ev.code}"
        return True


def make_services(max_items: int = 200):
    clock = FixedClock()
    db = Database(":memory:")
    args = (db, TZ, clock, max_items)
    return db, clock, TaskService(*args), ReminderService(*args), EmailService(*args)


def make_runtime(**overrides):
    from lily.config import Settings
    from lily.runtime import Runtime

    clock = FixedClock()
    settings = Settings(db_path=":memory:", rate_limit_per_min=1000, **overrides)
    return Runtime(settings, clock=clock), clock
