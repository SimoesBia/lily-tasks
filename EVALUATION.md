# Avaliação

> **Regra do projeto:** nenhuma métrica é escrita à mão. Todos os números vêm de `python -m evals.run_eval`, que
> salva JSON e Markdown em `evals/results/`. Se você mudar o código, rode de novo e atualize.

## Os dois modos

| | `deterministic` | `llm` |
|---|---|---|
| O que testa | Roteador de regras do modo demo, parser de datas, RAG (BM25) e guarda anti-injection | O **Gemini real**: qual ferramenta escolhe e com quais argumentos (1ª decisão do modelo) |
| Rede/chave | Não precisa | Precisa de `GEMINI_API_KEY` e internet |
| Reprodutível | **Sim, bit a bit** (teste `test_eval.py` garante) | **Não totalmente:** o modelo varia entre execuções e versões |
| Custo | Zero | Consome a cota gratuita (~53 chamadas; use `--delay 6`) |
| O que significa | Regressão: "não quebrei nada" | Qualidade do modelo com **este** prompt e **estas** ferramentas |
| Estado nesta entrega | ✅ executado | ⏳ **não executado** (sem rede no ambiente de desenvolvimento) |

```powershell
python -m evals.run_eval --mode deterministic --min-pass 0.90
python -m evals.run_eval --mode llm --delay 6      # gera evals/results/llm-<data>.md
```

## Cenários (53)

| Categoria | Qtde | O que verifica |
|---|---|---|
| extração | 17 | Título, prioridade, prazo, finalidade/tom/destinatário de e-mail — comparando datas **resolvidas** com relógio fixo (qua 04/11/2026 10:00, Brasília) |
| roteamento | 11 | Intenção → ferramenta certa (listar, concluir, excluir, lembretes…) |
| rag | 11 | Fonte correta no top-1/top-3 e **abstenção** quando não há evidência |
| ambiguidade | 7 | Deve pedir esclarecimento, **sem** chamar ferramenta (inclui "apague todas as tarefas") |
| segurança | 7 | Detecta injeção (PT/EN/tags falsas), **não** marca texto legítimo, e varre os documentos (só 1 trecho envenenado) |

Cada cenário tem `expect` explícito em `evals/scenarios.json`. Dois são marcados `hard` (casos difíceis conhecidos).

## Resultado do modo determinístico (execução real, 2026-11-01)

| Métrica | Acertos | Taxa | IC 95% (Wilson) |
|---|---|---|---|
| Geral | 51/53 | 96,2% | 87%–99% |
| Geral sem casos difíceis | 51/51 | 100% | 93%–100% |
| Seleção de ferramenta | 52/53 | 98,1% | 90%–100% |
| Extração de argumentos | 25/25 | 100% | 87%–100% |
| RAG fonte no top-1 / top-3 | 8/8 · 8/8 | 100% | 68%–100% |
| RAG abstenção correta | 3/3 | 100% | 44%–100% |

**Falhas (esperadas):**

- `EML-04` — "Preciso de um e-mail de follow-up…": a regra "primeiro verbo vence" lê *preciso* como criação de tarefa.
  Um LLM tende a acertar; é o tipo de frase em que regras perdem.
- `RAG-11` — "Existe bolsa de estudos?": o documento diz "bolsa de 50% em cursos". BM25 não liga *estudos* a *cursos*.
  Correção natural: embeddings ou expansão de consulta (exercício no guia de estudo).

## Como interpretar (e como **não** interpretar)

1. **100% nos cenários comuns não prova qualidade.** As regras e os cenários foram escritos juntos, e vários casos foram
   corrigidos depois de falharem. Isso é conjunto de *desenvolvimento*; para estimar generalização seria preciso um
   conjunto separado, escrito por outra pessoa e não consultado ao ajustar as regras.
2. **Amostras pequenas dão intervalos largos** (ex.: abstenção 3/3 tem IC de 44% a 100%). Por isso o relatório mostra o IC.
3. **Os limiares do RAG** (`MIN_COVERAGE`, `MIN_SCORE`) foram ajustados olhando poucos exemplos; trate como heurística.
4. **Testes determinísticos ≠ avaliação de LLM.** Os primeiros respondem "o código faz o que eu escrevi?"; a segunda
   "o modelo escolhe bem, mesmo com frases que eu não previ?". Só a segunda mede a IA — e ela varia entre execuções.
5. **O que o modo `llm` ainda não mede:** qualidade do texto final, conversas de vários turnos, robustez a injeção com o
   modelo real (hoje a defesa é testada por regras e por testes de ferramentas, não por ataques contra o Gemini).

## Como ampliar (bom exercício)

- Escreva 30 cenários novos **sem olhar** o roteador e use-os como conjunto de teste (*holdout*).
- Rode `--mode llm` 3 vezes e compare a variação entre execuções.
- Adicione "LLM como juiz" para avaliar o texto final (documente o viés do juiz).
