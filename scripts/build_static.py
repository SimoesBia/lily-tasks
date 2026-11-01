"""Gera static_space/index.html embutindo os mesmos documentos fictícios usados pelo RAG em Python."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
docs = [{"name": p.name, "content": p.read_text(encoding="utf-8")} for p in sorted((ROOT / "data" / "docs").glob("*.md"))]
html = (ROOT / "static_space" / "template.html").read_text(encoding="utf-8")
payload = json.dumps(docs, ensure_ascii=False).replace("</", "<\\/")
(ROOT / "static_space" / "index.html").write_text(html.replace("__DOCS__", payload), encoding="utf-8")
print(f"static_space/index.html gerado com {len(docs)} documentos.")
