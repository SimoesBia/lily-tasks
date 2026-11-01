"""Índice BM25 em Python puro (CPU, sem embeddings, sem dependências).

Escolha deliberada: para poucos documentos curtos, BM25 é rápido, explicável e roda em
qualquer notebook. Limitação: não entende sinônimos (ver ARCHITECTURE.md).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ..text import tokens

MIN_COVERAGE = 0.6  # fração (ponderada por idf) dos termos da pergunta presentes no melhor trecho
MIN_SCORE = 1.5  # BM25 mínimo do melhor trecho
MAX_CHUNK_CHARS = 700


@dataclass(frozen=True)
class Chunk:
    id: str
    doc: str
    title: str
    heading: str
    text: str

    @property
    def source(self) -> str:
        return f"{self.doc} › {self.heading}" if self.heading else self.doc


@dataclass
class Passage:
    chunk: Chunk
    score: float


@dataclass
class RetrievalResult:
    query: str
    passages: list[Passage] = field(default_factory=list)
    sufficient: bool = False
    coverage: float = 0.0
    reason: str = ""


def chunk_markdown(doc_name: str, content: str) -> list[Chunk]:
    title, sections, heading, buf = doc_name, [], "", []
    for line in content.splitlines():
        if line.startswith(">"):  # avisos/citações não são conteúdo recuperável
            continue
        if line.startswith("# ") and not sections and not buf:
            title = line[2:].strip()
        elif line.startswith("## "):
            if buf:
                sections.append((heading, "\n".join(buf).strip()))
            heading, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if buf:
        sections.append((heading, "\n".join(buf).strip()))
    chunks: list[Chunk] = []
    for heading, body in sections:
        if not body:
            continue
        parts, cur = [], ""
        for para in re.split(r"\n\s*\n", body):
            if cur and len(cur) + len(para) > MAX_CHUNK_CHARS:
                parts.append(cur)
                cur = ""
            cur = f"{cur}\n\n{para}".strip()
        parts.append(cur)
        for part in parts:
            chunks.append(Chunk(f"{doc_name}#{len(chunks) + 1}", doc_name, title, heading, part))
    return chunks


class DocumentIndex:
    K1, B = 1.5, 0.75

    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self._tf: list[Counter] = []
        df: Counter = Counter()
        for ch in chunks:
            # título e cabeçalho entram duas vezes: pesam mais que o corpo
            terms = tokens(ch.text) + 2 * tokens(f"{ch.title} {ch.heading}")
            tf = Counter(terms)
            self._tf.append(tf)
            df.update(tf.keys())
        self._df = df
        self._n = max(len(chunks), 1)
        self._avg = sum(sum(tf.values()) for tf in self._tf) / self._n if chunks else 1.0

    @classmethod
    def from_dir(cls, path: str | Path) -> DocumentIndex:
        chunks: list[Chunk] = []
        for f in sorted(Path(path).glob("*.md")):
            chunks.extend(chunk_markdown(f.name, f.read_text(encoding="utf-8")))
        return cls(chunks)

    def _idf(self, term: str) -> float:
        df = self._df.get(term, 0)
        return math.log(1 + (self._n - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 3) -> RetrievalResult:
        q = list(dict.fromkeys(tokens(query)))
        if not q or not self.chunks:
            return RetrievalResult(query, reason="Pergunta sem termos de busca úteis.")
        scored: list[tuple[float, int]] = []
        for i, tf in enumerate(self._tf):
            dl = sum(tf.values())
            s = 0.0
            for t in q:
                f = tf.get(t, 0)
                if f:
                    norm = f + self.K1 * (1 - self.B + self.B * dl / self._avg)
                    s += self._idf(t) * f * (self.K1 + 1) / norm
            scored.append((s, i))
        scored.sort(reverse=True)
        top = [(s, i) for s, i in scored[:k] if s > 0]
        if not top:
            return RetrievalResult(query, reason="Nenhum documento menciona os termos da pergunta.")
        best_tf = self._tf[top[0][1]]
        total = sum(self._idf(t) for t in q)
        matched = sum(self._idf(t) for t in q if t in best_tf)
        coverage = matched / total if total else 0.0
        sufficient = coverage >= MIN_COVERAGE and top[0][0] >= MIN_SCORE
        reason = "" if sufficient else (
            f"Evidência insuficiente (cobertura {coverage:.2f} < {MIN_COVERAGE} "
            f"ou score {top[0][0]:.2f} < {MIN_SCORE})."
        )
        passages = [Passage(self.chunks[i], round(s, 3)) for s, i in top]
        return RetrievalResult(query, passages, sufficient, round(coverage, 3), reason)
