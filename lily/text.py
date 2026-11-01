"""Normalização de texto em português (sem dependências externas)."""

from __future__ import annotations

import re
import unicodedata


def fold(text: str) -> str:
    """Minúsculas e sem acentos, preservando o comprimento para textos NFC.

    Isso permite usar índices de `fold(s)` para recortar `s` original.
    """
    nfc = unicodedata.normalize("NFC", text)
    decomposed = unicodedata.normalize("NFD", nfc)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").lower()


_TOKEN = re.compile(r"[a-z0-9]+")

STOPWORDS = frozenset(
    "a o as os um uma uns umas de do da dos das em no na nos nas por para pra com sem sobre "
    "entre e ou mas que se como qual quais quando onde quem quanto quantos quantas quanta "
    "ser sao foi tem ter tenho temos posso pode podem preciso minha meu minhas meus seu sua "
    "seus suas eu voce me te lhe ele ela eles elas isso isto esse essa esses essas este esta "
    "ao aos ja nao sim mais menos muito muita ate apos antes depois durante tambem so apenas "
    "qualquer cada todo toda todos todas fazer faz feito vai vou ha mim dele dela nosso nossa "
    "existe existem acho tipo favor gostaria saber queria devo deve devem quero valor".split()
)


def stem(token: str) -> str:
    """Stemming leve para plurais comuns do português."""
    t = token
    if len(t) > 5 and t.endswith("coes"):
        return t[:-4] + "cao"
    if len(t) > 4 and t.endswith("oes"):
        return t[:-3] + "ao"
    if len(t) > 4 and t.endswith("ais"):
        return t[:-3] + "al"
    if len(t) > 4 and t.endswith("eis"):
        return t[:-3] + "el"
    if len(t) > 4 and t.endswith("ns"):
        return t[:-2] + "m"
    if len(t) > 4 and t.endswith("res"):
        return t[:-2]
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def tokens(text: str, *, drop_stopwords: bool = True) -> list[str]:
    out = []
    for raw in _TOKEN.findall(fold(text)):
        if drop_stopwords and raw in STOPWORDS:
            continue
        out.append(stem(raw))
    return out
