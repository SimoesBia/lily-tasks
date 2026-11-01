"""Interpretação determinística de datas/horas em português do Brasil.

O LLM pode enviar ISO 8601 ou uma frase ("amanhã às 9h"); a resolução final é sempre
feita aqui, com o relógio e o fuso do servidor, e não pelo modelo.
"""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .errors import LilyError
from .text import fold

UTC = timezone.utc

_WORDS = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
    "sete": 7, "oito": 8, "nove": 9, "dez": 10, "quinze": 15, "vinte": 20, "trinta": 30,
}  # fmt: skip
_WEEKDAYS = {
    "segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6,
}  # fmt: skip
_PERIOD_DEFAULT_HOUR = {"manha": 9, "madrugada": 6, "tarde": 15, "noite": 20}
_WEEKDAY_ABBR = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

_NUM = r"(\d{1,3}|" + "|".join(_WORDS) + r")"
RE_HALF = re.compile(r"\b(?:daqui\s+(?:a\s+)?|em\s+)meia\s+hora\b")
RE_REL = re.compile(
    rf"\b(?:daqui\s+(?:a\s+)?|em\s+|dentro\s+de\s+){_NUM}\s+(minuto|hora|dia|semana|mes)(?:s|es)?\b"
)
RE_AFTER_TOMORROW = re.compile(r"\bdepois\s+de\s+amanha\b")
RE_TOMORROW = re.compile(r"\bamanha\b")
RE_TODAY = re.compile(r"\bhoje\b")
RE_DATE = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?(?![\d/])")
RE_WEEKDAY = re.compile(
    r"\b(?:proxim[oa]\s+)?(segunda|terca|quarta|quinta|sexta|sabado|domingo)(?:-feira)?\b"
)
RE_DAY = re.compile(r"\bdia\s+(\d{1,2})\b(?!\s*/)")
RE_COLON = re.compile(r"(?<![\d/:])(\d{1,2}):(\d{2})\b")
RE_H = re.compile(r"(?<![\d/:])(\d{1,2})\s*h(?![a-z])\s*(\d{2})?")
RE_HORAS = re.compile(r"(?<![\d/:])\b(\d{1,2})\s+horas?\b")
RE_AS = re.compile(r"\bas\s+(\d{1,2})\b(?!\s*[/:h]|\s*(?:dias?|horas?|minutos?|semanas?))")
RE_NOON = re.compile(r"\bmeio[\s-]dia\b")
RE_PERIOD = re.compile(r"\b(manha|tarde|noite|madrugada)\b")

_ORDERED = [
    RE_HALF, RE_REL, RE_AFTER_TOMORROW, RE_TOMORROW, RE_TODAY, RE_DATE, RE_WEEKDAY, RE_DAY,
    RE_COLON, RE_H, RE_HORAS, RE_AS, RE_NOON, RE_PERIOD,
]  # fmt: skip

EXAMPLES = "amanhã às 9h, sexta 14h30, daqui a 2 horas, dia 15 às 10h, 20/11 de manhã"


def _blank(s: str, m: re.Match) -> str:
    return s[: m.start()] + " " * (m.end() - m.start()) + s[m.end() :]


def _num(token: str) -> int:
    return int(token) if token.isdigit() else _WORDS[token]


def _add_months(d: date, months: int) -> date:
    idx = d.month - 1 + months
    year, month = d.year + idx // 12, idx % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def _try_iso(raw: str, tz: ZoneInfo) -> datetime | None:
    if not re.match(r"^\d{4}-\d{2}-\d{2}", raw):
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if len(raw) == 10:
        dt = dt.replace(hour=9, minute=0)
    return dt.replace(tzinfo=tz) if dt.tzinfo is None else dt.astimezone(tz)


def _parse_time(s: str) -> tuple[time | None, str | None, str]:
    """Extrai hora e período do dia. Retorna (hora, período, resto sem o trecho de hora)."""
    hour = minute = None
    for rx in (RE_COLON, RE_H, RE_HORAS, RE_AS):
        m = rx.search(s)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2)) if rx in (RE_COLON, RE_H) and m.group(2) else 0
            s = _blank(s, m)
            break
    if hour is None:
        m = RE_NOON.search(s)
        if m:
            hour, minute, s = 12, 0, _blank(s, m)
    period = None
    m = RE_PERIOD.search(s)
    if m:
        period = m.group(1)
        s = _blank(s, m)
    if hour is not None:
        if hour > 23 or minute > 59:  # type: ignore[operator]
            raise LilyError("invalid_date", "Horário inválido.")
        if period in ("tarde", "noite") and hour < 12:
            hour += 12
        return time(hour, minute or 0), period, s
    if period:
        return time(_PERIOD_DEFAULT_HOUR[period], 0), period, s
    return None, None, s


def resolve_when(
    text: str, now: datetime, tz: ZoneInfo, *, default_time: time = time(9, 0)
) -> datetime:
    """Converte uma frase ou ISO 8601 em datetime com fuso. Levanta LilyError se não entender."""
    raw = (text or "").strip()
    if not raw:
        raise LilyError("invalid_date", "Informe uma data/hora.")
    iso = _try_iso(raw, tz)
    if iso:
        return iso
    s = fold(raw)
    local_now = now.astimezone(tz)
    today = local_now.date()

    m = RE_HALF.search(s)
    if m:
        return (local_now + timedelta(minutes=30)).replace(second=0, microsecond=0)
    m = RE_REL.search(s)
    if m:
        n, unit = _num(m.group(1)), m.group(2)
        rest = _blank(s, m)
        if unit in ("minuto", "hora"):
            delta = timedelta(minutes=n) if unit == "minuto" else timedelta(hours=n)
            return (local_now + delta).replace(second=0, microsecond=0)
        base = {
            "dia": today + timedelta(days=n),
            "semana": today + timedelta(weeks=n),
            "mes": _add_months(today, n),
        }[unit]
        t, _, _ = _parse_time(rest)
        t = t or local_now.time().replace(second=0, microsecond=0)
        return datetime.combine(base, t, tzinfo=tz)

    d: date | None = None
    m = RE_AFTER_TOMORROW.search(s)
    if m:
        d, s = today + timedelta(days=2), _blank(s, m)
    if d is None:
        m = RE_TOMORROW.search(s)
        if m:
            d, s = today + timedelta(days=1), _blank(s, m)
    if d is None:
        m = RE_TODAY.search(s)
        if m:
            d, s = today, _blank(s, m)
    if d is None:
        m = RE_DATE.search(s)
        if m:
            day, month = int(m.group(1)), int(m.group(2))
            year_s = m.group(3)
            year = (int(year_s) + (2000 if len(year_s) == 2 else 0)) if year_s else today.year
            try:
                d = date(year, month, day)
            except ValueError as exc:
                raise LilyError("invalid_date", f"Data inexistente: {m.group(0)}.") from exc
            if not year_s and d < today:
                d = date(year + 1, month, day)
            s = _blank(s, m)
    if d is None:
        m = RE_WEEKDAY.search(s)
        if m:
            ahead = (_WEEKDAYS[m.group(1)] - today.weekday()) % 7 or 7
            d, s = today + timedelta(days=ahead), _blank(s, m)
    if d is None:
        m = RE_DAY.search(s)
        if m:
            day = int(m.group(1))
            year, month = today.year, today.month
            if day < today.day:
                nxt = _add_months(date(year, month, 1), 1)
                year, month = nxt.year, nxt.month
            if not 1 <= day <= calendar.monthrange(year, month)[1]:
                raise LilyError("invalid_date", f"O mês não tem o dia {day}.")
            d, s = date(year, month, day), _blank(s, m)

    t, _, _ = _parse_time(s)
    if d is None and t is None:
        raise LilyError(
            "invalid_date", f"Não entendi a data/hora “{raw}”. Exemplos: {EXAMPLES}."
        )
    if d is None:
        d = today
        if datetime.combine(d, t, tzinfo=tz) <= local_now:  # type: ignore[arg-type]
            d = today + timedelta(days=1)
    return datetime.combine(d, t or default_time, tzinfo=tz)


def split_when(text: str) -> tuple[str, str | None]:
    """Separa expressões temporais do texto. Retorna (texto sem a data, frase temporal)."""
    f = fold(text)
    spans: list[tuple[int, int]] = []
    for rx in _ORDERED:
        for m in rx.finditer(f):
            spans.append((m.start(), m.end()))
            f = _blank(f, m)
    if not spans:
        return text, None
    spans.sort()
    phrase = " ".join(text[a:b].strip() for a, b in spans)
    rest, last = [], 0
    for a, b in spans:
        rest.append(text[last:a])
        last = b
    rest.append(text[last:])
    return " ".join("".join(rest).split()), phrase


def to_utc_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def from_utc_iso(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def format_local(value: str | None, tz: ZoneInfo) -> str:
    """'2026-11-05T12:00:00Z' -> 'qui, 05/11 às 09:00' (no fuso informado)."""
    if not value:
        return "sem prazo"
    dt = from_utc_iso(value).astimezone(tz)
    return f"{_WEEKDAY_ABBR[dt.weekday()]}, {dt:%d/%m} às {dt:%H:%M}"
