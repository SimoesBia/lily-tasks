"""Defesa contra prompt injection em texto recuperado (documentos são DADOS, não instruções).

Camadas: (1) remoção de linhas suspeitas aqui; (2) o texto vai ao LLM marcado como não
confiável; (3) ferramentas que alteram dados são bloqueadas no turno em que houve suspeita;
(4) exclusões exigem confirmação fora do LLM. Nenhuma camada é perfeita sozinha.
"""

from __future__ import annotations

import re

from ..text import fold

_PATTERNS: dict[str, re.Pattern] = {
    "ignore_instructions_pt": re.compile(
        r"\bignor\w+\s+(?:\w+\s+){0,3}(?:instrucoes|regras|ordens|comandos)\b"
    ),
    "ignore_instructions_en": re.compile(
        r"\bignore\s+(?:\w+\s+){0,3}(?:instructions|rules|prompts?)\b"
    ),
    "role_override": re.compile(r"\b(?:voce agora e|a partir de agora voce|you are now|act as)\b"),
    "prompt_exfiltration": re.compile(
        r"\b(?:revele|mostre|exiba|reveal|show|print)\b.{0,40}"
        r"\b(?:prompt|chave|api key|senha|segredo|secret|token)\b"
    ),
    "tool_hijack": re.compile(
        r"\b(?:chame|invoque|execute|use|call|invoke|run)\b.{0,30}"
        r"\b(?:ferramenta|funcao|tool|function|comando|command|delete_\w+|create_\w+)\b"
    ),
    "mass_delete": re.compile(
        r"\b(?:apague|exclua|delete|remova|remove|wipe)\b.{0,20}\b(?:tod[oa]s|all|everything)\b"
    ),
    "fake_roles": re.compile(r"</?\s*(?:system|assistant|tool|instructions?)\s*>|\[/?inst\]"),
    "hide_from_user": re.compile(r"\bnao\s+(?:informe|diga|mencione|conte)\b.{0,20}\busuario\b"),
    "addressed_to_ai": re.compile(r"\bnota\s+para\s+(?:assistentes?|ia|modelos?)\b"),
}

REMOVED_MARK = "[trecho removido: possível instrução maliciosa]"


def scan(text: str) -> list[str]:
    """Nomes das regras acionadas no texto (vazio = sem suspeita)."""
    f = fold(text)
    return [name for name, rx in _PATTERNS.items() if rx.search(f)]


def sanitize(text: str) -> tuple[str, list[str]]:
    """Remove linhas suspeitas. Retorna (texto limpo, regras acionadas)."""
    flags: list[str] = []
    out: list[str] = []
    for line in text.splitlines():
        hit = scan(line)
        if hit:
            flags.extend(hit)
            if not out or out[-1] != REMOVED_MARK:
                out.append(REMOVED_MARK)
        else:
            out.append(line)
    return "\n".join(out), sorted(set(flags))
