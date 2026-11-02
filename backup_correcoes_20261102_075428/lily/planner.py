"""Roteador determinístico do MODO DEMONSTRAÇÃO (regras, sem LLM).

Transforma uma mensagem em português em chamadas de ferramenta ou em uma pergunta de
esclarecimento. É deliberadamente simples e previsível. A interface sempre rotula o modo
demonstração como simulado: estas respostas NÃO são geradas por um modelo de linguagem.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .dates import split_when
from .text import fold


@dataclass
class Plan:
    kind: str  # "tool" | "clarify" | "help"
    calls: list[dict] = field(default_factory=list)
    text: str | None = None


HELP = (
    "Posso criar, listar, editar, concluir e excluir tarefas; criar lembretes; rascunhar "
    "e-mails e responder perguntas sobre os documentos da empresa fictícia. "
    "Exemplo: “Crie uma tarefa para enviar o relatório amanhã às 9h com prioridade alta”."
)
CLARIFY_GENERIC = (
    "Não tenho certeza do que você quer fazer. " + HELP
)

_PRIORITY_RX = [
    re.compile(r"\bprioridade\s+(alta|media|baixa)\b"),
    re.compile(r"\b(alta|media|baixa)\s+prioridade\b"),
    re.compile(r"\b(urgente|importante|sem\s+pressa)\b"),
]
_INTENTS: list[tuple[str, re.Pattern]] = [
    ("delete", re.compile(r"\b(apag\w+|exclu\w+|delet\w+|remov\w+|cancel\w+|elimin\w+)\b")),
    ("update", re.compile(r"\b(edit\w+|alter\w+|mud\w+|renome\w+|atualiz\w+|troc\w+|reagend\w+|adie|adiar|posterg\w+|antecip\w+)\b")),
    ("list", re.compile(r"\b(list\w+|mostr\w+|exib\w+|veja|ver|quais|o que (?:tenho|falta)|minhas tarefas|meus lembretes|minha lista)\b")),
    ("complete", re.compile(r"\b(conclu\w+|finaliz\w+|termin\w+|complet\w+|ja fiz|fiz)\b|\bmar(?:c|qu)\w+(?=.*\b(?:feit[ao]|pront[ao]|complet[ao]|conclu\w+)\b)")),
    ("reminder", re.compile(r"\b(?:me\s+lembr\w+|lembre-?me|me\s+avis\w+|avise-?me|(?:cri\w+|adicion\w+|agend\w+|configur\w+)\s+(?:um\s+)?lembrete)\b|\blembretes?\b")),
    ("task", re.compile(r"\b(?:preciso|tenho que|tenho de|devo|(?:cri\w+|adicion\w+|anot\w+|cadastr\w+|inclu\w+)\s+(?:uma\s+|a\s+)?(?:nova\s+)?tarefa)\b|\btarefas?\b")),
    ("email", re.compile(r"\b(e-?mail|rascunho)\b")),
]  # fmt: skip
_PURPOSES = [
    ("thanks", r"agradec\w*|obrigad\w*"),
    ("apology", r"desculp\w*|pedir perdao|lamento"),
    ("meeting", r"reuni\w*|agendar conversa|marcar conversa|call"),
    ("follow_up", r"follow-?up|acompanh\w*|cobrar|retorno|andamento"),
    ("status_update", r"status|atualizacao|atualizar sobre|progresso"),
    ("introduction", r"apresent\w*"),
    ("request", r"solicit\w*|pedir|pedido|requisit\w*"),
]
_TONES = [
    ("formal", r"formal|respeitos\w*"),
    ("friendly", r"amig\w*|informal|descontra\w*|simpatic\w*"),
    ("direct", r"direto|objetivo|curto|sucinto"),
]
_QUESTION_START = re.compile(
    r"^(qual|quais|quanto|quantos|quantas|como|quando|onde|quem|o que|por que|porque|posso|pode|"
    r"existe|tem|preciso de|e obrigatorio|segundo|de acordo|nos documentos)\b"
)
_DOC_TOPICS = re.compile(
    r"\b(ferias|home ?office|remoto|reembolso|beneficio|vale|plano de saude|vpn|senha|mfa|"
    r"onboarding|notebook|politica|documento|regulamento|manual|guia|despesa|viagem)\b"
)


def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip(" ,.;:-–—\"'“”‘’()")
    prev = None
    while prev != s:
        prev = s
        s = re.sub(
            r"^(?:para|pra|de|do|da|que|a|o|as|os|um|uma|sobre|chamada|chamado|intitulada|com|e)\s+",
            "", s, flags=re.I,
        )  # fmt: skip
        s = re.sub(
            r"\s+(?:para|pra|de|do|da|em|no|na|as|às|a|ate|até|daqui|com|e|por|que)$",
            "", s, flags=re.I,
        )  # fmt: skip
        s = s.strip(" ,.;:-–—\"'“”‘’")
    return s


def _cut(orig: str, rx: re.Pattern) -> tuple[str, re.Match | None]:
    """Remove da string original a 1ª ocorrência de `rx` (casado sobre a versão sem acentos)."""
    f = fold(orig)
    m = rx.search(f)
    if not m:
        return orig, None
    return (orig[: m.start()] + " " + orig[m.end() :]), m


def _extract_priority(orig: str) -> tuple[str, str | None]:
    for rx in _PRIORITY_RX:
        orig, m = _cut(orig, rx)
        if m:
            word = (m.group(1) if m.groups() else m.group(0)).replace(" ", "")
            return orig, {"urgente": "alta", "importante": "alta", "sempressa": "baixa"}.get(word, word)
    return orig, None


def _capitalize(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _ref(orig: str, kind: str) -> str | None:
    """Número (#3, 'tarefa 3') ou trecho do título citado depois de 'tarefa'/'lembrete'."""
    f = fold(orig)
    m = re.search(rf"\b{kind}s?\s*(?:n[o°º]?\.?\s*)?#?(\d+)\b", f) or re.search(r"#(\d+)", f)
    if m:
        return m.group(1)
    m = re.search(rf"\b{kind}s?\b", f)
    if not m:
        return None
    frag = orig[m.end() :]
    frag = re.sub(
        r"\s+como\s+(?:feit\w+|conclu\w+|pront\w+|complet\w+)\s*$", "", frag, flags=re.I
    )
    frag = re.sub(r"\s+(?:como\s+)?(?:feit\w+|conclu\w+)\s*$", "", frag, flags=re.I)
    frag = _clean(frag)
    return frag or None


def _kind(f: str) -> str | None:
    if "lembrete" in f:
        return "lembrete"
    if "tarefa" in f:
        return "tarefa"
    return None


def plan(message: str) -> Plan:
    orig = " ".join(message.split())
    f = fold(orig)
    if not f:
        return Plan("clarify", text=CLARIFY_GENERIC)
    if re.match(r"^(oi|ola|bom dia|boa tarde|boa noite|e ai|hey|hello|ajuda|help)\b[\s!.?]*$", f):
        return Plan("help", text="Olá! " + HELP)

    best: tuple[int, int, str] | None = None
    for order, (name, rx) in enumerate(_INTENTS):
        m = rx.search(f)
        if m and (best is None or (m.start(), order) < (best[0], best[1])):
            best = (m.start(), order, name)
    intent = best[2] if best else None

    handler = {
        "delete": _plan_delete, "update": _plan_update, "list": _plan_list,
        "complete": _plan_complete, "reminder": _plan_reminder, "task": _plan_task,
        "email": _plan_email,
    }.get(intent or "")  # fmt: skip
    if handler:
        result = handler(orig, f)
        if result:
            return result
    if _QUESTION_START.match(f) or f.endswith("?") or _DOC_TOPICS.search(f):
        return Plan("tool", [{"name": "search_documents", "args": {"query": orig.rstrip("?! .")}}])
    return Plan("clarify", text=CLARIFY_GENERIC)


# ---- handlers ---------------------------------------------------------------------------
def _plan_delete(orig: str, f: str) -> Plan:
    kind = _kind(f)
    if re.search(r"\b(tod[oa]s|tudo)\b", f):
        return Plan("clarify", text="Por segurança, não excluo itens em massa. Diga qual item (número ou título).")
    if not kind:
        return Plan("clarify", text="O que você quer excluir: uma tarefa ou um lembrete? Informe também o número ou título.")
    ref = _ref(orig, kind)
    if not ref:
        return Plan("clarify", text=f"Qual {kind} devo excluir? Informe o número ou o título.")
    tool, key = ("delete_task", "task") if kind == "tarefa" else ("delete_reminder", "reminder")
    return Plan("tool", [{"name": tool, "args": {key: ref}}])


def _plan_complete(orig: str, f: str) -> Plan | None:
    if _kind(f) != "tarefa":
        return Plan("clarify", text="Qual tarefa devo concluir? Informe o número ou o título.")
    ref = _ref(orig, "tarefa")
    if not ref:
        return Plan("clarify", text="Qual tarefa devo concluir? Informe o número ou o título.")
    return Plan("tool", [{"name": "complete_task", "args": {"task": ref}}])


def _plan_list(orig: str, f: str) -> Plan | None:
    if "lembrete" in f:
        return Plan("tool", [{"name": "list_reminders", "args": {}}])
    if "tarefa" not in f and "lista" not in f and "o que" not in f:
        return None  # pergunta genérica ("quais os benefícios?") segue para a busca nos documentos
    args: dict = {}
    if re.search(r"\bconclu\w+|\bfeit[ao]s?\b", f):
        args["status"] = "concluida"
    elif re.search(r"\btod[ao]s\b", f):
        args["status"] = "todas"
    _, prio = _extract_priority(orig)
    if prio:
        args["priority"] = prio
    if re.search(r"\bhoje\b", f):
        args["due_before"] = "hoje 23:59"
    return Plan("tool", [{"name": "list_tasks", "args": args}])


def _plan_task(orig: str, f: str) -> Plan:
    text, prio = _extract_priority(orig)
    text, when = split_when(text)
    text = re.sub(
        r"^(?:por favor,?\s*)?(?:cri\w+|adicion\w+|anot\w+|cadastr\w+|inclu\w+)\s+(?:uma\s+|a\s+)?(?:nova\s+)?tarefa\b\s*",
        "", text, flags=re.I,
    )  # fmt: skip
    text = re.sub(r"^(?:nova\s+)?tarefa\b\s*", "", text, flags=re.I)
    text = re.sub(
        r"^(?:eu\s+)?(?:preciso|tenho que|tenho de|devo)\s+", "", text, flags=re.I
    )
    title = _capitalize(_clean(text))
    if not title:
        return Plan("clarify", text="Qual é o título da tarefa?")
    args: dict = {"title": title}
    if when:
        args["due"] = when
    if prio:
        args["priority"] = prio
    return Plan("tool", [{"name": "create_task", "args": args}])


def _plan_reminder(orig: str, f: str) -> Plan:
    text, when = split_when(orig)
    text = re.sub(
        r"^(?:por favor,?\s*)?(?:me\s+lembr\w+|lembre-?me|me\s+avis\w+|avise-?me|"
        r"(?:cri\w+|adicion\w+|agend\w+|configur\w+)\s+(?:um\s+)?lembrete)\b\s*",
        "", text, flags=re.I,
    )  # fmt: skip
    text = re.sub(r"^lembretes?\b\s*", "", text, flags=re.I)
    title = _capitalize(_clean(text))
    if not title:
        return Plan("clarify", text="Do que devo te lembrar?")
    if not when:
        return Plan("clarify", text="Quando devo te lembrar? Ex.: amanhã às 9h, sexta 14h, daqui a 2 horas.")
    return Plan("tool", [{"name": "create_reminder", "args": {"text": title, "when": when}}])


def _plan_update(orig: str, f: str) -> Plan | None:
    kind = _kind(f)
    if not kind:
        return Plan("clarify", text="O que você quer alterar: uma tarefa ou um lembrete? Informe o número.")
    m = re.search(rf"\b{kind}s?\s*(?:n[o°º]?\.?\s*)?#?(\d+)\b", f) or re.search(r"#(\d+)", f)
    if not m:
        return Plan("clarify", text=f"Qual {kind} devo alterar? Informe o número (ex.: {kind} 2).")
    ref = m.group(1)
    rest = orig[: m.start()] + " " + orig[m.end() :]
    rest, prio = _extract_priority(rest)
    quoted = re.search(r"[\"“'‘](.+?)[\"”'’]", rest)
    new_title = quoted.group(1).strip() if quoted else None
    if quoted:
        rest = rest[: quoted.start()] + " " + rest[quoted.end() :]
    clear = bool(re.search(r"\b(remova|tire|sem)\s+(?:o\s+)?prazo\b", fold(rest))) if kind == "tarefa" else False
    _, when = split_when(rest)
    if kind == "tarefa":
        args: dict = {"task": ref}
        if new_title:
            args["title"] = new_title
        if prio:
            args["priority"] = prio
        if clear:
            args["clear_due"] = True
        elif when:
            args["due"] = when
        if len(args) == 1:
            return Plan("clarify", text="O que devo alterar na tarefa: título, prazo ou prioridade?")
        return Plan("tool", [{"name": "update_task", "args": args}])
    args = {"reminder": ref}
    if new_title:
        args["text"] = new_title
    if when:
        args["when"] = when
    if len(args) == 1:
        return Plan("clarify", text="O que devo alterar no lembrete: o texto ou o horário?")
    return Plan("tool", [{"name": "update_reminder", "args": args}])


def _plan_email(orig: str, f: str) -> Plan:
    purpose = next((p for p, rx in _PURPOSES if re.search(rx, f)), None)
    if not purpose:
        return Plan(
            "clarify",
            text="Qual a finalidade do e-mail? (acompanhamento, solicitação, reunião, agradecimento, "
            "desculpas, atualização de status ou apresentação) E qual o tom: formal, amigável ou direto?",
        )
    tone = next((t for t, rx in _TONES if re.search(rx, f)), "neutral")
    args: dict = {"purpose": purpose, "tone": tone}
    m = re.search(r"\bpara\s+(?:o\s+|a\s+)?([A-ZÀ-Ú][\wÀ-ú]+(?:\s+[A-ZÀ-Ú][\wÀ-ú]+)?)", orig)
    if m:
        args["recipient"] = m.group(1)
    t = re.search(r"\b(?:sobre|dizendo que|avisando que|informando que)\s+(.+)$", orig, flags=re.I)
    if t:
        args["key_points"] = [_clean(t.group(1))]
    return Plan("tool", [{"name": "draft_email", "args": args}])
