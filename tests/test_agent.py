from lily.agent import DEMO_PREFIX
from lily.llm.base import LLMError, LLMTurn, ToolCall
from tests.helpers import expect_error, make_runtime

A = "a" * 16


class ScriptedLLM:
    """LLM falso e determinístico: devolve turnos pré-definidos e registra o que recebeu."""

    def __init__(self, turns):
        self.turns, self.seen = list(turns), []

    def generate(self, system, messages, tools):
        self.seen.append((system, [dict(m) for m in messages], tools))
        step = self.turns.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    def generate_structured(self, prompt, schema):
        raise LLMError("unavailable")


def test_demo_mode_is_always_labelled_as_simulated():
    rt, _ = make_runtime()
    for msg in ("Liste minhas tarefas", "oi", "amanhã", "Crie uma tarefa para estudar"):
        r = rt.agent.chat(A, msg)
        assert r.mode == "demo" and r.reply.startswith(DEMO_PREFIX)


def test_demo_flow_with_confirmation_buttons():
    rt, _ = make_runtime()
    rt.agent.chat(A, "Preciso comprar leite")
    r = rt.agent.chat(A, "Apague a tarefa comprar leite")
    assert r.pending and len(rt.tasks.list(A)) == 1
    assert "excluída" in rt.agent.confirm(A, r.pending["token"]).reply
    assert rt.tasks.list(A, status="todas") == []


def test_real_mode_runs_the_tool_loop_and_hides_ui_fields_from_the_model():
    rt, _ = make_runtime()
    llm = ScriptedLLM([
        LLMTurn(tool_calls=[ToolCall("create_task", {"title": "Enviar proposta", "due": "amanhã 9h", "priority": "alta"})]),
        LLMTurn(text="Pronto, criei a tarefa."),
    ])  # fmt: skip
    r = rt.agent.chat(A, "crie uma tarefa para enviar a proposta amanhã", llm)
    assert r.mode == "real" and r.reply == "Pronto, criei a tarefa."
    assert r.tool_events[0]["tool"] == "create_task" and rt.tasks.list(A)[0]["title"] == "Enviar proposta"
    system, messages, _ = llm.seen[1]
    tool_msg = [m for m in messages if m["role"] == "tool"][0]
    assert "display" not in tool_msg["result"] and "token" not in tool_msg["result"]
    assert "NUNCA" not in system or "Lily" in system


def test_real_mode_sensitive_tool_is_not_executed_by_the_model():
    rt, _ = make_runtime()
    rt.tasks.create(A, "Importante")
    llm = ScriptedLLM([LLMTurn(tool_calls=[ToolCall("delete_task", {"task": "1"})]), LLMTurn(text="Aguardando sua confirmação.")])
    r = rt.agent.chat(A, "apague a tarefa 1", llm)
    assert r.pending and len(rt.tasks.list(A)) == 1


def test_model_cannot_invent_arguments_or_tools():
    rt, _ = make_runtime()
    llm = ScriptedLLM([
        LLMTurn(tool_calls=[ToolCall("create_task", {"title": "x", "admin": True}), ToolCall("exec", {"code": "1"})]),
        LLMTurn(text="Não consegui."),
    ])  # fmt: skip
    r = rt.agent.chat(A, "faça algo", llm)
    assert [e["status"] for e in r.tool_events] == ["erro", "erro"] and rt.tasks.list(A, status="todas") == []


def test_provider_failures_become_friendly_messages_and_do_not_corrupt_history():
    rt, _ = make_runtime()
    r = rt.agent.chat(A, "oi", ScriptedLLM([LLMError("rate_limit", retryable=True)]))
    assert r.error == "rate_limit" and "cota" in r.reply
    ok = rt.agent.chat(A, "oi de novo", ScriptedLLM([LLMTurn(text="Olá!")]))
    assert ok.reply == "Olá!"


def test_loop_is_bounded():
    rt, _ = make_runtime(max_tool_steps=3)
    llm = ScriptedLLM([LLMTurn(tool_calls=[ToolCall("list_tasks", {})]) for _ in range(5)])
    r = rt.agent.chat(A, "liste sem parar", llm)
    assert r.error == "max_steps" and len(llm.turns) == 2


def test_input_limits_and_rate_limit():
    rt, _ = make_runtime(max_message_chars=50)
    with expect_error("message_too_long"):
        rt.agent.chat(A, "x" * 51)
    with expect_error("invalid_arguments"):
        rt.agent.chat(A, "   ")
    from lily.agent import RateLimiter

    t = [0.0]
    rl = RateLimiter(2, clock=lambda: t[0])
    rl.check("s")
    rl.check("s")
    with expect_error("rate_limited"):
        rl.check("s")
    t[0] = 61
    rl.check("s")  # janela deslizante liberou


def test_server_key_is_not_used_on_public_spaces_unless_allowed():
    from lily.config import Settings

    base = dict(gemini_api_key="AIza" + "k" * 35)
    assert Settings(**base).env_llm_enabled
    assert not Settings(**base, public_space=True).env_llm_enabled
    assert Settings(**base, public_space=True, allow_shared_key=True).env_llm_enabled
    assert not Settings(**base, force_demo=True).env_llm_enabled
    rt, _ = make_runtime()
    with expect_error("invalid_key"):
        rt.llm_for("curta")
