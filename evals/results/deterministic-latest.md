# Resultado da avaliação — modo `deterministic`
_Gerado em 2026-11-01T18:16:51-03:00. Cenários: 53._

| Métrica | Acertos | Taxa | IC 95% (Wilson) |
|---|---|---|---|
| Geral | 51/53 | 96.2% | 87%–99% |
| Geral (sem casos difíceis) | 51/51 | 100.0% | 93%–100% |
| Seleção de ferramenta | 52/53 | 98.1% | 90%–100% |
| Extração de argumentos | 25/25 | 100.0% | 87%–100% |
| RAG: fonte correta no top-1 | 8/8 | 100.0% | 68%–100% |
| RAG: fonte correta no top-3 | 8/8 | 100.0% | 68%–100% |
| RAG: abstenção correta | 3/3 | 100.0% | 44%–100% |

| Categoria | Acertos | Taxa | IC 95% |
|---|---|---|---|
| ambiguidade | 7/7 | 100.0% | 65%–100% |
| extracao | 17/17 | 100.0% | 82%–100% |
| rag | 10/11 | 90.9% | 62%–98% |
| roteamento | 10/11 | 90.9% | 62%–98% |
| seguranca | 7/7 | 100.0% | 65%–100% |

## Falhas
- **EML-04** _(caso difícil)_: “Preciso de um e-mail de follow-up para a Fernanda sobre a proposta” → ferramenta: esperado draft_email, obtido create_task
- **RAG-11** _(caso difícil)_: “Existe bolsa de estudos?” → suficiência: esperado True, obtido False
