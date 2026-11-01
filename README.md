---
title: Lily Tasks
emoji: 🪻
colorFrom: purple
colorTo: green
sdk: gradio
app_file: app.py
pinned: false
license: mit
short_description: Assistente de produtividade com IA (tool calling, RAG, FastAPI)
---

# Lily Tasks — AI Productivity Assistant

Assistente de produtividade em português que **conversa, executa ações reais** (tarefas, lembretes, rascunhos de
e-mail) e **responde sobre documentos com fontes**. Projeto de portfólio para a trilha **AI Engineer**: o foco não é
"chamar um LLM", e sim o que o cerca — validação, segurança, falhas, avaliação e honestidade sobre limites.

> **Demonstração:** [Gradio Space](https://huggingface.co/spaces/SEU-USUARIO/lily-tasks) · [Demo estática](https://huggingface.co/spaces/SEU-USUARIO/lily-tasks-static) _(troque `SEU-USUARIO` após publicar; veja [DEPLOYMENT.md](DEPLOYMENT.md))_

## Problema e solução

Assistentes de IA costumam falhar em três pontos: **inventam** (dizem que fizeram algo que não fizeram), **obedecem
texto malicioso** escondido em documentos e **não têm como ser medidos**. A Lily trata o LLM como um componente
não confiável dentro de uma arquitetura que impõe regras por código:

| Risco | Como é tratado |
|---|---|
| Parâmetros inventados pelo modelo | Validação estrita com Pydantic (`extra="forbid"`, enums); erro volta ao modelo |
| Exclusão acidental ou induzida | Confirmação **fora do LLM** (botões/token de uso único, escopo por sessão) |
| Prompt injection em documentos | Linhas suspeitas removidas + trechos marcados como dados + escrita bloqueada no turno |
| "Notificação" falsa | Estados explícitos: *registrado* → *vencido, não notificado* → *notificado (in-app)* |
| Resposta sem evidência | RAG com cobertura mínima; abstém-se e diz que não encontrou |
| Falha/limite da API | Timeout, retries com backoff+jitter, mensagens claras, loop de ferramentas limitado |
| Dados de um visitante vazarem para outro | Toda linha tem `session_id`; confirmações e IDs são por sessão |
| Medir qualidade | 53 cenários reproduzíveis + intervalos de confiança ([EVALUATION.md](EVALUATION.md)) |

## Funcionalidades

- **Chat** em linguagem natural com *tool calling* real (Gemini) e histórico da sessão.
- **Tarefas:** criar, listar (filtros), editar, concluir, excluir, prioridade e prazo.
- **Lembretes:** datas relativas em português ("sexta 14h", "daqui a 2 horas") com **fuso configurável**.
- **E-mails:** rascunhos editáveis (finalidade + tom). **Não existe código de envio.**
- **RAG:** 5 documentos fictícios, BM25 em Python puro (CPU), respostas com fonte `arquivo › seção`.
- **Painéis** de tarefas, lembretes, e-mails e atividade (ferramentas executadas), atualizados a cada ação.
- **Dois modos:** *real* (Gemini) e *demonstração simulada* (regras, sem chave, rotulado em toda resposta).

## Tecnologias

Python 3.11+ · FastAPI · Pydantic v2 · SDK oficial `google-genai` · SQLite · Gradio · Pytest · Ruff · GitHub Actions.
Sem GPU, sem banco externo, sem frameworks de agentes. Cabe em ~6 GB de RAM.

## Decisões técnicas (resumo)

1. **Interface `LLMClient` neutra** — o agente não conhece o SDK; os testes usam um LLM falso determinístico.
2. **Datas resolvidas no servidor**, não pelo modelo (LLMs erram "próxima sexta"); o modelo só repassa a frase.
3. **BM25 em vez de embeddings** — explicável, leve, sem download de modelo; limitação conhecida: sem sinônimos.
4. **Confirmação fora do LLM** — um modelo (ou um documento) convencido a apagar não consegue apagar.
5. **Isolamento por `session_id`** + numeração por sessão (#1, #2…) + TTL que apaga sessões inativas.
6. **Logs só com metadados** (ferramenta, status) e redação de chaves; o conteúdo das conversas não é logado.

Detalhes e diagramas: [ARCHITECTURE.md](ARCHITECTURE.md) · segurança: [SECURITY.md](SECURITY.md).

## Resultados verificáveis

Medidos por `python -m evals.run_eval --mode deterministic` (53 cenários, execução reproduzível):

| Métrica | Resultado | IC 95% |
|---|---|---|
| Cenários aprovados | 51/53 (96,2%) | 87%–99% |
| Seleção de ferramenta | 52/53 (98,1%) | 90%–100% |
| Extração de argumentos | 25/25 | 87%–100% |
| RAG fonte correta (top-3) / abstenção correta | 8/8 · 3/3 | — |

As 2 falhas são **casos difíceis deixados de propósito** (mostram os limites das regras e do BM25). **Leia a ressalva:**
esse modo avalia o *roteador de regras do modo demo*, e os cenários foram escritos pela mesma pessoa que escreveu as
regras — é um teste de regressão, **não** uma estimativa de generalização. A métrica que importa para o modelo real é
`--mode llm` (precisa da sua chave; **ainda não foi executada**). Veja [EVALUATION.md](EVALUATION.md).

### Estado de validação desta entrega

| Item | Situação |
|---|---|
| Datas, SQLite, serviços, RAG, guarda anti-injection, roteador, avaliação | **Executados** (37 testes passaram) |
| Ferramentas e agente (loop, confirmação, bloqueio, rate limit, erros do LLM) | **Executados** (18 testes), mas com um *stub* mínimo no lugar do `pydantic` — rode com o pydantic real |
| Lógica do Static Space (JS) | **Executada** em Node (datas, roteador, RAG, remoção de injeção) |
| API FastAPI, esquema Pydantic→Gemini, `pytest`, `ruff`, CI | **Escritos, não executados** (sem rede no ambiente de desenvolvimento) |
| Interface Gradio, chamadas reais ao Gemini, deploy no Hugging Face, Windows 11 | **Não testados** — siga o passo a passo e reporte erros |

## Como executar (Windows 11 — PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env        # opcional: cole sua GEMINI_API_KEY (modo real)
python app.py                 # interface em http://127.0.0.1:7860
pytest                        # testes
ruff check .                  # lint
python -m evals.run_eval --mode deterministic
uvicorn lily.api:create_app --factory --reload   # API em http://127.0.0.1:8000/docs
```

Sem `GEMINI_API_KEY` o app abre em **modo demonstração simulada**. Passo a passo completo (GitHub, Hugging Face,
LinkedIn): [docs/TUTORIAL_WINDOWS.md](docs/TUTORIAL_WINDOWS.md). Estudo e entrevista: [docs/GUIA_DE_ESTUDO.md](docs/GUIA_DE_ESTUDO.md).

## Estrutura

```
app.py                  entrada do Space/local (Gradio)        static_space/   demo 100% navegador
lily/ config · db · dates · text · planner(demo) · tools · agent · runtime · api · ui · render · theme
lily/services/          tasks · reminders · emails              lily/rag/       index (BM25) · guard
lily/llm/               base · gemini · retry                   data/docs/      documentos FICTÍCIOS
evals/                  scenarios.json · run_eval.py            tests/          67 testes
```

## Limitações conhecidas

- Lembretes só notificam com o app aberto (não há scheduler/push/e-mail) — por design e sinalizado na interface.
- BM25 não entende sinônimos ("bolsa de estudos" não acha "bolsa de 50% em cursos").
- Numa camada gratuita do Gemini, o Google pode usar os dados enviados para melhorar produtos (confira os termos
  atuais): **não use dados reais sensíveis** no modo real.
- O modo demo entende frases comuns; frases fora do padrão caem em esclarecimento.

Licença MIT. Todos os documentos em `data/docs/` são fictícios.
