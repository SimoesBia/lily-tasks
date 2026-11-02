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
class PendingOp:
    """Operação que aguarda uma resposta curta do usuário (ex.: 'qual tarefa?')."""

    kind: str  # "update" | "complete" | "delete"
    target: str  # "tarefa" | "lembrete"
    ref: str | None = None  # número ou trecho do nome; None = ainda não informado
    fields: dict = field(default_factory=dict)  # campos já conhecidos (priority, due, title, when, text…)
    field_hint: str | None = None  # campo citado sem valor ("prioridade" -> priority)


@dataclass
class Plan:
    kind: str  # "tool" | "clarify" | "help"
    calls: list[dict] = field(default_factory=list)
    text: str | None = None
    pending: PendingOp | None = None  # a guardar na sessão (None = nada pendente)
    on_fail: PendingOp | None = None  # a guardar se a ferramenta não achar/desambiguar o item


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


def plan(message: str, pending: PendingOp | None = None) -> Plan:
    orig = " ".join(message.split())
    f = fold(orig)
    if not f:
        return Plan("clarify", text=CLARIFY_GENERIC)
    if pending is not None:
        continued = _continue_pending(pending, orig, f)
        if continued is not None:
            return continued
        # não era resposta à pergunta: a pendência é descartada e a frase é roteada como nova
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
    if re.search(r"\b(?:remov\w+|tir\w+|apag\w+|exclu\w+|elimin\w+)\s+(?:o\s+|a\s+)?(?:prazo|prioridade|data)\b", f):
        return _plan_update(orig, f)  # tirar um CAMPO do item não é excluir o item
    kind = _kind(f)
    if re.search(r"\b(tod[oa]s|tudo)\b", f):
        return Plan("clarify", text="Por segurança, não excluo itens em massa. Diga qual item (número ou título).")
    if not kind:
        return Plan("clarify", text="O que você quer excluir: uma tarefa ou um lembrete? Informe também o número ou título.")
    ref = _ref(orig, kind)
    return _advance(PendingOp("delete", kind, ref))


def _plan_complete(orig: str, f: str) -> Plan | None:
    if _kind(f) != "tarefa":
        return _advance(PendingOp("complete", "tarefa"))
    return _advance(PendingOp("complete", "tarefa", _ref(orig, "tarefa")))


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
    ref_only = re.fullmatch(r"(?:a\s+|o\s+)?tarefa\s*(?:n[o°º]?\.?\s*|numero\s*)?#?(\d+)", f.strip(" .!?"))
    if ref_only:  # "tarefa 1" / "a tarefa 3" sem contexto: não é um título de tarefa
        n = ref_only.group(1)
        return Plan(
            "clarify",
            text=f"Não entendi “{orig}”. Você quer concluir, editar ou excluir a tarefa {n}? "
            f"Diga, por exemplo: “concluir tarefa {n}”.",
        )
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
    if re.fullmatch(r"#?\d+", title):  # "tarefa 1" sem contexto não é uma tarefa chamada "1"
        return Plan(
            "clarify",
            text=f"Não entendi “{orig}”. Você quer concluir, editar ou excluir a tarefa {title.lstrip('#')}? "
            f"Diga, por exemplo: “concluir tarefa {title.lstrip('#')}”.",
        )
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


# ---- edição e operações pendentes ---------------------------------------------------------
_PRIO_WORDS = {"alta": "alta", "urgente": "alta", "media": "media", "medio": "media", "normal": "media", "baixa": "baixa"}
_PRIO_WORD_RX = re.compile(r"\b(alta|urgente|media|medio|normal|baixa)\b")
_NUM_ONLY = re.compile(r"^(?:a\s+|o\s+|da\s+|de\s+)?(?:(?:tarefa|lembrete)\s*)?(?:n[o°º]?\.?\s*|numero\s*)?#?(\d+)$")
_ABORT = {"cancelar", "cancela", "deixa", "deixa pra la", "deixa para la", "deixa quieto", "esquece",
          "esqueca", "nao", "nada", "nao quero"}  # fmt: skip
_COMMAND_VERB = re.compile(
    r"\b(cri\w+|adicion\w+|anot\w+|cadastr\w+|inclu\w+|apag\w+|exclu\w+|delet\w+|remov\w+|cancel\w+|list\w+|"
    r"mostr\w+|exib\w+|conclu\w+|finaliz\w+|termin\w+|complet\w+|edit\w+|alter\w+|mud\w+|renome\w+|"
    r"atualiz\w+|troc\w+|me\s+lembr\w+|lembre-?me|escrev\w+|quais|preciso|tenho que)\b"
)  # fmt: skip
_ASK = {
    "priority": "Qual a nova prioridade: baixa, média ou alta?",
    "due": "Para quando devo mudar o prazo? Ex.: sexta, amanhã às 9h ou “sem prazo”.",
    "title": "Qual o novo título?",
    "when": "Para qual horário devo mover o lembrete? Ex.: amanhã às 9h.",
    "text": "Qual o novo texto do lembrete?",
}
_TOOL = {
    ("update", "tarefa"): ("update_task", "task"),
    ("update", "lembrete"): ("update_reminder", "reminder"),
    ("complete", "tarefa"): ("complete_task", "task"),
    ("delete", "tarefa"): ("delete_task", "task"),
    ("delete", "lembrete"): ("delete_reminder", "reminder"),
}
_VERB_INF = {"update": "alterar", "complete": "concluir", "delete": "excluir"}


def _field_name(target: str, word: str) -> str | None:
    base = {"prioridade": "priority", "prazo": "due", "data": "due", "vencimento": "due", "horario": "due",
            "hora": "due", "titulo": "title", "nome": "title", "texto": "title"}.get(word)  # fmt: skip
    if base is None:
        return None
    if target == "lembrete":  # lembretes não têm prioridade nem título: têm horário e texto
        return {"due": "when", "title": "text"}.get(base)
    return base


def _hint(target: str, f: str) -> str | None:
    for word in ("prioridade", "prazo", "vencimento", "data", "horario", "hora", "titulo", "nome", "texto"):
        if re.search(rf"\b{word}\b", f):
            hint = _field_name(target, word)
            if hint:
                return hint
    return None


def _parse_fields(target: str, text: str, hint: str | None = None, value: str | None = None) -> dict:
    """Extrai campos e valores novos. `value` = trecho que veio depois de 'para' (ou a resposta inteira)."""
    fields: dict = {}
    quoted = re.search(r"[\"“'‘](.+?)[\"”'’]", text)
    if quoted:
        fields["title" if target == "tarefa" else "text"] = quoted.group(1).strip()
        text = text[: quoted.start()] + " " + text[quoted.end() :]
    f = fold(text)
    if target == "tarefa":
        if re.search(r"\b(?:remov\w+|tire|tirar|sem)\s+(?:o\s+)?prazo\b", f):
            fields["clear_due"] = True
        found = list(_PRIO_WORD_RX.finditer(f))
        if found:
            solo = value is not None and re.fullmatch(
                r"\W*(?:(?:para|como|em|a)\s+)?(?:prioridade\s+)?(?:alta|urgente|media|medio|normal|baixa)\W*",
                fold(value),
            )
            if hint == "priority" or re.search(r"\bprioridade\b", f) or solo:
                fields["priority"] = _PRIO_WORDS[found[-1].group(1)]
    if not fields.get("clear_due"):
        _, when = split_when(text)
        if when:
            fields["due" if target == "tarefa" else "when"] = when
    return fields


def _split_name_value(target: str, tail: str, free_value: bool) -> tuple[str, str]:
    """Separa 'Estudar Python para média' em (nome, valor). Usa o ÚLTIMO 'para' que introduz um valor."""
    ft = fold(tail)
    for m in reversed(list(re.finditer(r"\s(?:para|pra)\s", ft))):
        name, value = tail[: m.start()], tail[m.end() :]
        if _parse_fields(target, value, value=value) or (free_value and value.strip()):
            return name, value
    m = re.search(r"\s(?:com\s+|de\s+|em\s+)?(?:prioridade|prazo)\b", ft)
    if m:
        return tail[: m.start()], tail[m.start() :]
    return tail, ""


def _split_ref(orig: str, f: str, target: str) -> tuple[str | None, str, str]:
    """Acha o item (número ou nome) e devolve (ref, texto antes, texto com o valor novo)."""
    m = re.search(rf"\b{target}s?\s*(?:n[o°º]?\.?\s*|numero\s*)?#?(\d+)\b", f) or re.search(r"#(\d+)", f)
    if m:
        return m.group(1), orig[: m.start()], orig[m.end() :]
    m = re.search(rf"\b{target}s?\b", f)
    if not m:
        return None, orig, ""
    head, tail = orig[: m.start()], orig[m.end() :]
    name, value = _split_name_value(target, tail, bool(re.search(r"\brenome\w+", f)))
    return (_clean(name) or None), head, value


def _advance(op: PendingOp) -> Plan:
    """Decide o próximo passo: perguntar o que falta (guardando a pendência) ou executar a ferramenta."""
    if not op.ref:
        return Plan(
            "clarify",
            text=f"Qual {op.target} devo {_VERB_INF[op.kind]}? Informe o número ou o nome (ex.: {op.target} 2).",
            pending=op,
        )
    label = f"#{op.ref}" if op.ref.isdigit() else f"“{op.ref}”"
    if op.kind == "update" and not op.fields:
        if op.field_hint:
            return Plan("clarify", text=_ASK[op.field_hint], pending=op)
        what = "título, prazo ou prioridade" if op.target == "tarefa" else "o texto ou o horário"
        return Plan("clarify", text=f"O que devo alterar na {op.target} {label}: {what}?", pending=op)
    tool, key = _TOOL[(op.kind, op.target)]
    args = {key: op.ref, **op.fields} if op.kind == "update" else {key: op.ref}
    return Plan("tool", [{"name": tool, "args": args}], on_fail=op)


def _continue_pending(op: PendingOp, orig: str, f: str) -> Plan | None:
    """Interpreta uma resposta curta como continuação de `op`. None = não é resposta (rotear como nova frase)."""
    bare = f.strip(" .!?,;:")
    if not bare:
        return None
    if bare in _ABORT:
        return Plan("clarify", text="Certo, cancelei essa operação. Nada foi alterado.")
    if op.ref is None:  # faltava QUAL item
        m = _NUM_ONLY.match(bare)
        if m:
            op.ref = m.group(1)
            return _advance(op)
        if re.match(rf"^(?:a\s+|o\s+)?{op.target}s?\b", bare):  # "tarefa 1", "tarefa Estudar Python para alta"
            ref, head, value = _split_ref(orig, f, op.target)
            if not ref:
                return None
            op.ref = ref
            op.fields.update(_parse_fields(op.target, f"{head} {value}", value=value))
            return _advance(op)
        if len(bare.split()) <= 6 and not _COMMAND_VERB.search(bare) and not _QUESTION_START.match(bare):
            op.ref = _clean(orig) or None  # "Estudar Python"
            return _advance(op) if op.ref else None
        return None
    if op.kind == "update" and not op.fields:  # faltava O QUE alterar / o valor novo
        if _COMMAND_VERB.search(bare):
            return None
        new = _parse_fields(op.target, orig, hint=op.field_hint, value=orig)
        if new:
            op.fields, op.field_hint = new, None
            return _advance(op)
        named = _field_name(op.target, re.sub(r"^(?:a|o|do|da|de)\s+", "", bare))
        if named:
            op.field_hint = named
            return _advance(op)
        if op.field_hint in ("title", "text") and len(orig) <= 150:
            op.fields, op.field_hint = {op.field_hint: _clean(orig)}, None
            return _advance(op)
    return None


def _plan_update(orig: str, f: str) -> Plan | None:
    target = _kind(f)
    if not target:
        return Plan("clarify", text="O que você quer alterar: uma tarefa ou um lembrete? Informe também o número ou o nome.")
    ref, head, value = _split_ref(orig, f, target)
    fields = _parse_fields(target, f"{head} {value}", value=value)
    if not fields and re.search(r"\brenome\w+", f):  # "renomeie a tarefa 4 para Enviar proposta" (sem aspas)
        free = _clean(re.sub(r"^\s*(?:para|pra)\s+", "", value, flags=re.I))
        if free:
            fields["title" if target == "tarefa" else "text"] = free
    hint = None if fields else _hint(target, fold(f"{head} {value}"))
    return _advance(PendingOp("update", target, ref, fields, hint))


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
