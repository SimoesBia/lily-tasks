from evals import run_eval


def test_scenario_set_is_large_and_varied():
    scenarios = run_eval.DATA["scenarios"]
    assert len(scenarios) >= 30
    assert {s["category"] for s in scenarios} >= {"roteamento", "extracao", "rag", "ambiguidade", "seguranca"}


def test_deterministic_eval_is_reproducible_and_above_threshold():
    first = run_eval.run("deterministic", 0)
    second = run_eval.run("deterministic", 0)
    strip = lambda r: {k: v for k, v in r.items() if k != "generated_at"}  # noqa: E731
    assert strip(first) == strip(second)
    assert first["overall_without_hard"]["rate"] >= 0.9
    # casos difíceis conhecidos devem continuar visíveis, não escondidos
    assert {f["id"] for f in first["failures"]} <= {"EML-04", "RAG-11"}
