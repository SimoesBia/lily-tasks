from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from ..db import Database
from ..errors import LilyError
from ..text import fold

Clock = Callable[[], datetime]


class BaseService:
    def __init__(
        self, db: Database, default_tz: str, clock: Clock, max_items: int = 200
    ) -> None:
        self.db = db
        self.default_tz = default_tz
        self.clock = clock
        self.max_items = max_items

    def tz(self, session_id: str) -> ZoneInfo:
        name = self.db.get_timezone(session_id) or self.default_tz
        try:
            return ZoneInfo(name)
        except Exception:  # fuso inválido salvo -> usa o padrão
            return ZoneInfo(self.default_tz)

    def now(self):
        return self.clock()

    @staticmethod
    def find_by_ref(rows: list[dict], ref: str, text_key: str, label: str) -> dict:
        """Resolve 'número' ou 'trecho do título' para uma única linha, sem adivinhar."""
        ref = str(ref).strip().lstrip("#").strip()
        if not ref:
            raise LilyError("invalid_arguments", f"Informe o número ou o título da {label}.")
        if ref.isdigit():
            for r in rows:
                if r["seq"] == int(ref):
                    return r
            raise LilyError("not_found", f"A {label} #{ref} não existe.", status=404)
        needle = fold(ref)
        exact = [r for r in rows if fold(r[text_key]) == needle]
        hits = exact or [r for r in rows if needle in fold(r[text_key])]
        if not hits:
            raise LilyError("not_found", f"Nenhuma {label} corresponde a “{ref}”.", status=404)
        if len(hits) > 1:
            raise LilyError(
                "ambiguous",
                f"Mais de uma {label} corresponde a “{ref}”. Informe o número.",
                status=409,
                candidates=[{"seq": r["seq"], "title": r[text_key]} for r in hits[:5]],
            )
        return hits[0]
