"""Regressão dos 3 bugs do modo demonstração, de ponta a ponta (Agent + ferramentas + SQLite)."""

from lily.llm.base import LLMTurn
from tests.helpers import make_runtime

A, B = "a" * 16, "b" * 16


def prio(rt, sid, seq):
    return next(t for t in rt.tasks.list(sid, status="todas") if t["seq"] == seq)["priority"]


def tools_used(result):
    return [e["tool"] for e in result.tool_events]


def test_bug1_edit_by_name_updates_the_existing_task():
    rt, _ = make_runtime()
    rt.tasks.create(A, "Estudar Python", priority="alta")
    r = rt.agent.chat(A, "Altere a prioridade da tarefa Estudar Python para média.")
    assert tools_used(r) == ["update_task"] and r.tool_events[0]["status"] == "ok"
    assert "Qual tarefa" not in r.reply and prio(rt, A, 1) == "media"
    assert len(rt.tasks.list(A, status="todas")) == 1


def test_bug1_ambiguous_name_is_not_guessed_and_the_number_answer_resolves_it():
    rt, _ = make_runtime()
    rt.tasks.create(A, "Estudar Python", priority="alta")
    rt.tasks.create(A, "Estudar Java", priority="alta")
    r = rt.agent.chat(A, "Altere a prioridade da tarefa Estudar para baixa")
    assert r.tool_events[0]["status"] == "erro" and "#1" in r.reply and "#2" in r.reply
    assert prio(rt, A, 1) == prio(rt, A, 2) == "alta"  # nada foi alterado
    r = rt.agent.chat(A, "2")
    assert tools_used(r) == ["update_task"] and prio(rt, A, 2) == "baixa" and prio(rt, A, 1) == "alta"


def test_bug1_unknown_name_keeps_asking_instead_of_creating_anything():
    rt, _ = make_runtime()
    r = rt.agent.chat(A, "Altere a prioridade da tarefa Inexistente para alta")
    assert "Nenhuma tarefa" in r.reply and rt.tasks.list(A, status="todas") == []
    rt.tasks.create(A, "Estudar Python")
    r = rt.agent.chat(A, "Estudar Python")
    assert tools_used(r) == ["update_task"] and prio(rt, A, 1) == "alta"


def test_bug2_clarification_answer_does_not_create_a_task():
    rt, _ = make_runtime()
    rt.tasks.create(A, "Estudar Python", priority="alta")
    r = rt.agent.chat(A, "Altere a prioridade da tarefa para média.")
    assert "Qual tarefa devo alterar" in r.reply and r.tool_events == []
    r = rt.agent.chat(A, "tarefa 1")
    assert tools_used(r) == ["update_task"] and "create_task" not in tools_used(r)
    assert len(rt.tasks.list(A, status="todas")) == 1 and prio(rt, A, 1) == "media"


def test_bug2_bare_task_number_never_becomes_a_task_called_1():
    rt, _ = make_runtime()
    r = rt.agent.chat(A, "tarefa 1")
    assert r.tool_events == [] and rt.tasks.list(A, status="todas") == []


def test_bug3_full_command_updates_priority_directly():
    rt, _ = make_runtime()
    rt.tasks.create(A, "Estudar Python", priority="alta")
    r = rt.agent.chat(A, "Altere a prioridade da tarefa 1 para média.")
    assert tools_used(r) == ["update_task"] and prio(rt, A, 1) == "media"
    assert "título, prazo ou prioridade" not in r.reply


def test_bug3_field_then_value_does_not_lose_context():
    rt, _ = make_runtime()
    rt.tasks.create(A, "Estudar Python", priority="alta")
    assert "O que devo alterar" in rt.agent.chat(A, "Altere a tarefa 1").reply
    assert "nova prioridade" in rt.agent.chat(A, "prioridade").reply
    r = rt.agent.chat(A, "média")
    assert tools_used(r) == ["update_task"] and prio(rt, A, 1) == "media"
    assert "Não tenho certeza" not in r.reply


def test_pending_is_isolated_per_session():
    rt, _ = make_runtime()
    rt.tasks.create(A, "Tarefa de A", priority="alta")
    rt.agent.chat(A, "Altere a prioridade da tarefa para baixa")
    r = rt.agent.chat(B, "tarefa 1")  # B não tem pendência nem tarefas
    assert r.tool_events == [] and rt.tasks.list(B, status="todas") == [] and prio(rt, A, 1) == "alta"
    r = rt.agent.chat(A, "tarefa 1")  # a pendência de A continua intacta
    assert tools_used(r) == ["update_task"] and prio(rt, A, 1) == "baixa"


def test_delete_clarification_still_requires_confirmation():
    rt, _ = make_runtime()
    rt.tasks.create(A, "Estudar Python")
    rt.agent.chat(A, "Apague a tarefa")
    r = rt.agent.chat(A, "tarefa 1")
    assert r.pending and len(rt.tasks.list(A)) == 1  # nada apagado sem confirmar
    assert rt.agent.confirm(B, r.pending["token"]).error == "not_found"  # outra sessão não confirma
    assert "excluída" in rt.agent.confirm(A, r.pending["token"]).reply
    assert rt.tasks.list(A, status="todas") == []


def test_new_command_or_expiry_discards_the_pending_operation():
    rt, clock = make_runtime()
    rt.tasks.create(A, "Estudar Python", priority="alta")
    rt.agent.chat(A, "Altere a prioridade da tarefa para baixa")
    r = rt.agent.chat(A, "Crie uma tarefa para estudar inglês")
    assert tools_used(r) == ["create_task"]
    assert rt.agent.chat(A, "tarefa 1").tool_events == [] and prio(rt, A, 1) == "alta"  # pendência já descartada
    rt.agent.chat(A, "Altere a prioridade da tarefa para baixa")
    clock.advance(minutes=11)  # pergunta expirada
    assert rt.agent.chat(A, "tarefa 1").tool_events == [] and prio(rt, A, 1) == "alta"


def test_real_mode_does_not_touch_or_inherit_demo_pending():
    rt, _ = make_runtime()
    rt.tasks.create(A, "Estudar Python", priority="alta")
    rt.agent.chat(A, "Altere a prioridade da tarefa para baixa")

    class Echo:
        def generate(self, system, messages, tools):
            return LLMTurn(text="ok")

    assert rt.agent.chat(A, "oi", Echo()).reply == "ok"
    assert rt.agent.chat(A, "tarefa 1").tool_events == [] and prio(rt, A, 1) == "alta"
