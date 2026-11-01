from datetime import datetime
from zoneinfo import ZoneInfo

from lily.dates import format_local, resolve_when, split_when, to_utc_iso
from tests.helpers import expect_error

TZ = ZoneInfo("America/Sao_Paulo")
NOW = datetime.fromisoformat("2026-11-04T10:00:00-03:00")  # quarta-feira


def at(text: str) -> str:
    return resolve_when(text, NOW, TZ).strftime("%Y-%m-%dT%H:%M")


def test_relative_days_and_time():
    assert at("amanhã às 9h") == "2026-11-05T09:00"
    assert at("depois de amanhã à tarde") == "2026-11-06T15:00"
    assert at("hoje 23:59") == "2026-11-04T23:59"
    assert at("em 3 dias às 8h") == "2026-11-07T08:00"


def test_durations():
    assert at("daqui a 2 horas") == "2026-11-04T12:00"
    assert at("daqui a meia hora") == "2026-11-04T10:30"
    assert at("daqui a duas semanas às 10h") == "2026-11-18T10:00"


def test_weekdays_are_always_in_the_future():
    assert at("sexta 14h30") == "2026-11-06T14:30"
    assert at("quarta") == "2026-11-11T09:00"  # hoje é quarta: vai para a próxima
    assert at("próxima segunda") == "2026-11-09T09:00"


def test_explicit_dates():
    assert at("dia 15 às 10h") == "2026-11-15T10:00"
    assert at("20/11 de manhã") == "2026-11-20T09:00"
    assert at("02/01") == "2027-01-02T09:00"  # sem ano e já passou -> próximo ano
    assert at("2026-11-10T15:00:00-03:00") == "2026-11-10T15:00"


def test_only_time_rolls_to_tomorrow_when_passed():
    assert at("às 9") == "2026-11-05T09:00"
    assert at("meio-dia") == "2026-11-04T12:00"


def test_invalid_input_raises_clear_errors():
    for bad in ("", "xyz", "30/02", "dia 31 de nada às 25h"):
        with expect_error("invalid_date"):
            resolve_when(bad, NOW, TZ)


def test_split_when_keeps_title_words():
    rest, phrase = split_when("Entregar 3 relatórios dia 15 às 9h30")
    assert "3 relatórios" in rest and "dia 15" in phrase
    assert split_when("Comprar leite") == ("Comprar leite", None)


def test_formatting_and_utc_roundtrip():
    iso = to_utc_iso(resolve_when("amanhã às 9h", NOW, TZ))
    assert iso == "2026-11-05T12:00:00Z"
    assert format_local(iso, TZ) == "qui, 05/11 às 09:00"
    assert format_local(None, TZ) == "sem prazo"
