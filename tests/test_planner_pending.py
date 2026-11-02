"""Regressão dos 3 bugs do modo demonstração (nível do planner; só biblioteca padrão)."""

from lily.planner import PendingOp, plan


def call(p):
    assert p.kind == "tool", f"esperava ferramenta, veio {p.kind}: {p.text}"
    return p.calls[0]["name"], p.calls[0]["args"]


def test_bug1_edit_by_task_name():
    p = plan("Altere a prioridade da tarefa Estudar Python para média.")
    assert call(p) == ("update_task", {"task": "Estudar Python", "priority": "media"})


def test_bug1_names_containing_para_and_other_fields():
    assert call(plan("Altere a prioridade da tarefa Ligar para Ana para alta"))[1] == {"task": "Ligar para Ana", "priority": "alta"}
    assert call(plan("Mude o prazo da tarefa Estudar Python para sexta"))[1] == {"task": "Estudar Python", "due": "sexta"}
    assert call(plan("Altere a tarefa Estudar Python para prioridade baixa"))[1] == {"task": "Estudar Python", "priority": "baixa"}
    assert call(plan("Renomeie a tarefa Estudar Python para 'Estudar FastAPI'"))[1] == {"task": "Estudar Python", "title": "Estudar FastAPI"}
    assert call(plan("Altere o lembrete ligar para a Ana para amanhã às 10h"))[1]["reminder"] == "ligar para a Ana"


def test_bug2_short_answer_continues_the_pending_edit():
    first = plan("Altere a prioridade da tarefa para média.")
    assert first.kind == "clarify" and isinstance(first.pending, PendingOp) and first.pending.fields == {"priority": "media"}
    second = plan("tarefa 1", pending=first.pending)
    assert call(second) == ("update_task", {"task": "1", "priority": "media"})
    assert second.pending is None  # pendência consumida


def test_bug2_task_number_without_context_never_creates_a_task():
    for msg in ("tarefa 1", "tarefa #2", "a tarefa 3"):
        p = plan(msg)
        assert p.kind == "clarify" and not p.calls, msg


def test_bug2_answer_forms_are_all_accepted():
    for answer in ("1", "tarefa 1", "a tarefa 1", "#1", "tarefa nº 1", "tarefa número 1"):
        first = plan("Altere a prioridade da tarefa para alta")
        assert call(plan(answer, pending=first.pending)) == ("update_task", {"task": "1", "priority": "alta"}), answer
    first = plan("Altere a prioridade da tarefa para alta")
    assert call(plan("Estudar Python", pending=first.pending))[1] == {"task": "Estudar Python", "priority": "alta"}


def test_bug3_full_command_is_executed_in_one_message():
    assert call(plan("Altere a prioridade da tarefa 1 para média.")) == ("update_task", {"task": "1", "priority": "media"})
    assert call(plan("Altere o prazo da tarefa 2 para amanhã às 9h"))[1] == {"task": "2", "due": "amanhã 9h"}
    assert call(plan("Remova o prazo da tarefa 2"))[1] == {"task": "2", "clear_due": True}


def test_bug3_field_then_value_keeps_the_context():
    p = plan("Altere a tarefa 1")
    assert p.kind == "clarify" and p.pending.ref == "1"
    p = plan("prioridade", pending=p.pending)
    assert p.kind == "clarify" and "prioridade" in p.text.lower() and p.pending.field_hint == "priority"
    assert call(plan("média", pending=p.pending)) == ("update_task", {"task": "1", "priority": "media"})
    p = plan("Altere a tarefa 1")
    assert call(plan("prioridade alta", pending=p.pending))[1] == {"task": "1", "priority": "alta"}
    p = plan("Altere a tarefa 1")
    p = plan("prazo", pending=p.pending)
    assert call(plan("sexta", pending=p.pending))[1] == {"task": "1", "due": "sexta"}


def test_a_new_command_drops_the_pending_operation():
    pend = plan("Altere a prioridade da tarefa para média").pending
    name, args = call(plan("Crie uma tarefa para estudar inglês", pending=pend))
    assert name == "create_task" and "estudar" in args["title"].lower()
    assert call(plan("Liste minhas tarefas", pending=pend))[0] == "list_tasks"
    assert plan("cancelar", pending=pend).kind == "clarify"


def test_complete_and_delete_clarifications_are_also_pending_and_stay_destructive_safe():
    p = plan("Conclua a tarefa")
    assert call(plan("tarefa 2", pending=p.pending)) == ("complete_task", {"task": "2"})
    p = plan("Apague a tarefa")
    assert p.pending.kind == "delete"
    assert call(plan("2", pending=p.pending)) == ("delete_task", {"task": "2"})  # a confirmação continua no registro
    assert plan("apague todas as tarefas").kind == "clarify"


def test_reminder_edit_by_number_and_unrelated_text_is_not_swallowed():
    p = plan("Altere o lembrete 2 para amanhã às 10h")
    assert call(p)[0] == "update_reminder" and call(p)[1]["reminder"] == "2"
    pend = plan("Altere a prioridade da tarefa para média").pending
    assert plan("Quantos dias de férias eu tenho?", pending=pend).calls[0]["name"] == "search_documents"
