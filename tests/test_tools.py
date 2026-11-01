from lily.tools import ToolContext
from tests.helpers import make_runtime

A, B = "a" * 16, "b" * 16


def test_invalid_arguments_are_rejected_without_echoing_input():
    rt, _ = make_runtime()
    res = rt.registry.execute(ToolContext(A), "create_task", {"title": "x", "priority": "urgentissima", "hack": 1})
    assert res["ok"] is False and res["error"] == "invalid_arguments"
    assert "urgentissima" not in str(res)  # o valor digitado não é devolvido/logado
    assert rt.tasks.list(A, status="todas") == []


def test_unknown_tool_is_refused():
    rt, _ = make_runtime()
    assert rt.registry.execute(ToolContext(A), "run_shell", {"cmd": "rm -rf /"})["error"] == "unknown_tool"
    assert not any("shell" in n or "exec" in n for n in rt.registry.names)


def test_delete_requires_confirmation_and_is_session_scoped():
    rt, _ = make_runtime()
    rt.tasks.create(A, "Comprar leite")
    res = rt.registry.execute(ToolContext(A), "delete_task", {"task": "1"})
    assert res["status"] == "needs_confirmation" and len(rt.tasks.list(A)) == 1  # nada foi apagado ainda
    assert rt.registry.confirm(B, res["token"])["ok"] is False  # outro visitante não confirma
    assert len(rt.tasks.list(A)) == 1
    done = rt.registry.confirm(A, res["token"])
    assert done["ok"] and rt.tasks.list(A, status="todas") == []
    assert rt.registry.confirm(A, res["token"])["ok"] is False  # token de uso único


def test_cancel_keeps_data():
    rt, _ = make_runtime()
    rt.reminders.create(A, "Ligar", "amanhã 9h")
    res = rt.registry.execute(ToolContext(A), "delete_reminder", {"reminder": "ligar"})
    assert rt.registry.cancel(A, res["token"])["status"] == "cancelled"
    assert len(rt.reminders.list(A)) == 1


def test_ambiguous_reference_returns_candidates_instead_of_guessing():
    rt, _ = make_runtime()
    rt.tasks.create(A, "Comprar leite")
    rt.tasks.create(A, "Comprar pão")
    res = rt.registry.execute(ToolContext(A), "complete_task", {"task": "comprar"})
    assert res["error"] == "ambiguous" and len(res["candidates"]) == 2


def test_injection_in_retrieved_docs_blocks_mutating_tools_for_the_turn():
    rt, _ = make_runtime()
    ctx = ToolContext(A)
    res = rt.registry.execute(ctx, "search_documents", {"query": "aviso importante instruções ferramenta delete_task"})
    assert res["ok"] and ctx.tainted and res["security_flags"]
    assert all("IGNORE" not in p["text"] for p in res.get("passages", []))
    blocked = rt.registry.execute(ctx, "create_task", {"title": "x"})
    assert blocked["error"] == "blocked_untrusted_context" and rt.tasks.list(A) == []
    # leitura continua permitida; e um turno novo (novo contexto) não herda a suspeita
    assert rt.registry.execute(ctx, "list_tasks", {})["ok"]
    assert rt.registry.execute(ToolContext(A), "create_task", {"title": "ok"})["ok"]


def test_search_without_evidence_says_so():
    rt, _ = make_runtime()
    res = rt.registry.execute(ToolContext(A), "search_documents", {"query": "preço do bitcoin hoje"})
    assert res["ok"] and res["sufficient"] is False and res["passages"] == []


def test_email_tool_never_sends_and_falls_back_to_template_when_llm_fails():
    rt, _ = make_runtime()

    class BrokenLLM:
        def generate_structured(self, prompt, schema):
            raise RuntimeError("falha simulada")

    res = rt.registry.execute(ToolContext(A, llm=BrokenLLM()), "draft_email",
                              {"purpose": "meeting", "tone": "friendly", "recipient": "Ana"})  # fmt: skip
    assert res["ok"] and res["draft"]["generated_by"] == "template" and "NÃO foi enviado" in res["display"]


def test_tool_log_stores_metadata_only():
    rt, _ = make_runtime()
    rt.registry.execute(ToolContext(A), "create_task", {"title": "Meu segredo de trabalho"})
    logs = rt.db.recent_tool_logs(A)
    assert logs[0]["tool"] == "create_task" and logs[0]["status"] == "ok"
    assert "segredo" not in str(logs)
