"""Avaliação reproduzível do comportamento da Lily.

Dois modos (ver EVALUATION.md):
  deterministic  Roteador de regras (modo demo) + parser de datas + RAG + guarda anti-injection.
                 Não usa rede nem LLM; é um teste de regressão, não prova de generalização.
  llm            Mesmos cenários com o Gemini real (precisa de GEMINI_API_KEY e internet).
                 Mede só a PRIMEIRA decisão do modelo (qual ferramenta e quais argumentos),
                 sem executar nada.

Uso:
  python -m evals.run_eval --mode deterministic --min-pass 0.85
  python -m evals.run_eval --mode llm --delay 6
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lily.dates import resolve_when  # noqa: E402
from lily.errors import LilyError  # noqa: E402
from lily.planner import plan as demo_plan  # noqa: E402
from lily.rag import guard  # noqa: E402
from lily.rag.index import DocumentIndex  # noqa: E402
from lily.text import fold  # noqa: E402

DATA = json.loads((ROOT / "evals" / "scenarios.json").read_text(encoding="utf-8"))
TZ = ZoneInfo(DATA["timezone"])
NOW = datetime.fromisoformat(DATA["now"])
INDEX = DocumentIndex.from_dir(ROOT / "data" / "docs")


def wilson(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confiança de Wilson (95%) para uma proporção."""
    if total == 0:
        return 0.0, 0.0
    p = passed / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def check_args(args: dict, expect: dict, absent: list[str]) -> list[str]:
    errors = []
    for key, want in expect.items():
        if key.endswith("_local"):
            field = {"due_local": "due", "when_local": "when"}[key]
            try:
                got = resolve_when(str(args.get(field, "")), NOW, TZ).strftime("%Y-%m-%dT%H:%M")
            except LilyError:
                got = None
            if got != want:
                errors.append(f"{field}: esperado {want}, obtido {got}")
        elif key.endswith("_contains"):
            field = key[: -len("_contains")]
            if fold(want) not in fold(str(args.get(field, ""))):
                errors.append(f"{field} deveria conter “{want}”, obtido “{args.get(field)}”")
        else:
            if fold(str(args.get(key, ""))) != fold(str(want)):
                errors.append(f"{key}: esperado {want!r}, obtido {args.get(key)!r}")
    for key in absent:
        if args.get(key):
            errors.append(f"{key} não deveria ser preenchido (obtido {args.get(key)!r})")
    return errors


def eval_rag(query: str, expect: dict) -> dict:
    res = INDEX.search(query)
    out = {"sufficient": res.sufficient, "errors": []}
    if res.sufficient != expect["sufficient"]:
        out["errors"].append(f"suficiência: esperado {expect['sufficient']}, obtido {res.sufficient}")
    if expect.get("source") and res.passages:
        docs = [p.chunk.doc for p in res.passages]
        out["hit1"] = docs[0] == expect["source"]
        out["hit3"] = expect["source"] in docs
        if not out["hit3"]:
            out["errors"].append(f"fonte {expect['source']} fora do top-3 ({docs})")
    elif expect.get("source"):
        out["hit1"] = out["hit3"] = False
        out["errors"].append("nenhum trecho recuperado")
    return out


def run_security(sc: dict) -> dict:
    if sc.get("doc_scan"):
        flagged = sum(1 for c in INDEX.chunks if guard.scan(c.text))
        ok = flagged == sc["expect"]["flagged_chunks"]
        return {"passed": ok, "errors": [] if ok else [f"trechos suspeitos: {flagged}"]}
    flagged = bool(guard.scan(sc["injection_text"]))
    ok = flagged == sc["expect"]["flagged"]
    return {"passed": ok, "errors": [] if ok else [f"flagged={flagged}, esperado {sc['expect']['flagged']}"]}


def decide_deterministic(message: str) -> tuple[str | None, dict]:
    p = demo_plan(message)
    if p.kind == "tool" and p.calls:
        return p.calls[0]["name"], p.calls[0]["args"]
    return None, {}


def make_llm_decider(delay: float):
    from lily.agent import build_system_prompt
    from lily.config import Settings
    from lily.runtime import Runtime

    rt = Runtime(Settings.from_env())
    llm = rt.llm_for(None)
    if llm is None:
        sys.exit("Defina GEMINI_API_KEY (e LILY_FORCE_DEMO=0) para usar --mode llm.")
    system = build_system_prompt(NOW, str(TZ))
    tools = rt.registry.declarations()

    def decide(message: str) -> tuple[str | None, dict]:
        time.sleep(delay)  # respeita limites da camada gratuita
        turn = llm.generate(system, [{"role": "user", "text": message}], tools)
        if turn.tool_calls:
            return turn.tool_calls[0].name, turn.tool_calls[0].args
        return None, {}

    return decide


def run(mode: str, delay: float) -> dict:
    decide = decide_deterministic if mode == "deterministic" else make_llm_decider(delay)
    results = []
    for sc in DATA["scenarios"]:
        if sc["category"] == "seguranca":
            if mode == "llm":
                continue  # defesa determinística; não depende do modelo
            r = run_security(sc)
            results.append({**{k: sc[k] for k in ("id", "category")}, "hard": False, **r, "tool_ok": r["passed"]})
            continue
        exp = sc["expect"]
        errors: list[str] = []
        try:
            tool, args = decide(sc["message"])
            err_kind = None
        except Exception as exc:  # noqa: BLE001 - falha de API conta como erro, não como acerto
            tool, args, err_kind = None, {}, type(exc).__name__
            errors.append(f"erro do provedor: {err_kind}")
        tool_ok = tool == exp["tool"] and not err_kind
        if not tool_ok and not err_kind:
            errors.append(f"ferramenta: esperado {exp['tool']}, obtido {tool}")
        arg_ok = None
        if tool_ok and exp.get("args") is not None:
            arg_errors = check_args(args, exp["args"], exp.get("absent", []))
            arg_ok = not arg_errors
            errors += arg_errors
        rag = None
        if exp.get("rag"):
            query = args.get("query") or sc["message"]
            rag = eval_rag(query, exp["rag"])
            errors += rag["errors"]
        results.append({
            "id": sc["id"], "category": sc["category"], "hard": sc.get("hard", False),
            "message": sc["message"], "tool": tool, "args": args, "tool_ok": tool_ok,
            "arg_ok": arg_ok, "rag": rag, "passed": not errors, "errors": errors,
        })  # fmt: skip
    return summarize(mode, results)


def summarize(mode: str, results: list[dict]) -> dict:
    def rate(items, key="passed"):
        n = len(items)
        k = sum(1 for r in items if r.get(key))
        lo, hi = wilson(k, n)
        return {"passed": k, "total": n, "rate": round(k / n, 3) if n else 0.0, "ci95": [round(lo, 3), round(hi, 3)]}

    by_cat: dict[str, list] = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)
    with_args = [r for r in results if r.get("arg_ok") is not None]
    rag_rows = [r["rag"] for r in results if r.get("rag") and "hit1" in r["rag"]]
    abst = [r for r in results if r.get("rag") and r["rag"] is not None and "hit1" not in r["rag"]]
    return {
        "mode": mode,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scenarios": len(results),
        "overall": rate(results),
        "overall_without_hard": rate([r for r in results if not r["hard"]]),
        "tool_selection": rate([r for r in results if "tool_ok" in r], "tool_ok"),
        "argument_extraction": rate(with_args, "arg_ok"),
        "rag_hit_at_1": rate([{"x": r["hit1"]} for r in rag_rows], "x"),
        "rag_hit_at_3": rate([{"x": r["hit3"]} for r in rag_rows], "x"),
        "rag_abstention_correct": rate(abst),
        "by_category": {c: rate(v) for c, v in sorted(by_cat.items())},
        "failures": [
            {"id": r["id"], "hard": r["hard"], "message": r.get("message", ""), "errors": r["errors"]}
            for r in results if not r["passed"]
        ],
        "results": results,
    }


def to_markdown(rep: dict) -> str:
    def row(name, m):
        return f"| {name} | {m['passed']}/{m['total']} | {m['rate']:.1%} | {m['ci95'][0]:.0%}–{m['ci95'][1]:.0%} |"

    lines = [
        f"# Resultado da avaliação — modo `{rep['mode']}`",
        f"_Gerado em {rep['generated_at']}. Cenários: {rep['scenarios']}._", "",
        "| Métrica | Acertos | Taxa | IC 95% (Wilson) |", "|---|---|---|---|",
        row("Geral", rep["overall"]), row("Geral (sem casos difíceis)", rep["overall_without_hard"]),
        row("Seleção de ferramenta", rep["tool_selection"]),
        row("Extração de argumentos", rep["argument_extraction"]),
        row("RAG: fonte correta no top-1", rep["rag_hit_at_1"]),
        row("RAG: fonte correta no top-3", rep["rag_hit_at_3"]),
        row("RAG: abstenção correta", rep["rag_abstention_correct"]), "",
        "| Categoria | Acertos | Taxa | IC 95% |", "|---|---|---|---|",
    ]
    lines += [row(c, m) for c, m in rep["by_category"].items()]
    lines += ["", "## Falhas"]
    if not rep["failures"]:
        lines.append("Nenhuma.")
    for f in rep["failures"]:
        tag = " _(caso difícil)_" if f["hard"] else ""
        lines.append(f"- **{f['id']}**{tag}: “{f['message']}” → " + "; ".join(f["errors"]))
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["deterministic", "llm"], default="deterministic")
    ap.add_argument("--delay", type=float, default=6.0, help="pausa entre chamadas (modo llm)")
    ap.add_argument("--min-pass", type=float, default=None, help="falha (exit 1) se a taxa geral ficar abaixo")
    ap.add_argument("--out", default=str(ROOT / "evals" / "results"))
    args = ap.parse_args()
    rep = run(args.mode, args.delay)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = "latest" if args.mode == "deterministic" else datetime.now().strftime("%Y%m%d-%H%M%S")
    (out / f"{args.mode}-{stamp}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    md = to_markdown(rep)
    (out / f"{args.mode}-{stamp}.md").write_text(md, encoding="utf-8")
    print(md)
    if args.min_pass is not None and rep["overall"]["rate"] < args.min_pass:
        print(f"FALHOU: taxa geral {rep['overall']['rate']:.1%} < {args.min_pass:.0%}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
