# Guia de estudo, entrevista e exercícios

## Parte 1 — Como o projeto funciona (leia na ordem)

**1. `lily/config.py` → `runtime.py`.** `Settings.from_env()` lê variáveis (e `.env`). `Runtime` monta tudo: banco,
serviços, índice RAG, registro de ferramentas e agente. Um detalhe de segurança: `env_llm_enabled` só libera a chave do
servidor fora de Space público (ou com `LILY_ALLOW_SHARED_KEY`).

**2. `db.py`.** SQLite com uma conexão por transação (`BEGIN IMMEDIATE`). Toda tabela tem `session_id`; tarefas,
lembretes e rascunhos têm `seq` por sessão. `purge_stale` apaga sessões inativas; `put_pending/take_pending` guardam ações
sensíveis aguardando confirmação (uso único, escopo por sessão, expira em 10 min).

**3. `dates.py`.** `resolve_when(frase, agora, fuso)` transforma "sexta 14h30" em datetime. A técnica: normalizar acentos
(`fold`), achar um padrão, **apagá-lo da string** (`_blank`) para não ser lido de novo (ex.: o "2" de "2 horas" não vira
horário). `split_when` separa a data do título ("Enviar relatório" + "amanhã 9h").

**4. `services/*`.** Regras de negócio sem LLM. `BaseService.find_by_ref` resolve "3" ou "comprar leite" e **nunca
adivinha**: ambíguo → `LilyError("ambiguous", candidates=[...])`. Lembretes têm estado calculado (`registrado`,
`vencido_sem_notificacao`, `notificado`); só `mark_notified` muda isso.

**5. `rag/index.py`.** Divide Markdown por `##`, tokeniza (sem acentos, sem stopwords, stemming leve), pontua com BM25 e decide
se há evidência: `coverage` = fração do peso (idf) dos termos da pergunta presentes no melhor trecho. Abaixo de 0,6 → "não sei".

**6. `rag/guard.py`.** Regras que reconhecem instruções disfarçadas de conteúdo ("ignore as instruções anteriores",
"chame a ferramenta…"). `sanitize` remove só as linhas suspeitas.

**7. `schemas.py` + `tools.py`.** Cada ferramenta = modelo Pydantic (`extra="forbid"`) + função. `execute()` faz: nome
existe? → valida → contexto suspeito bloqueia escrita? → é sensível? (cria pendência e **retorna sem executar**) → executa →
registra só metadados. `to_gemini_schema` converte o JSON Schema do Pydantic para o formato das declarações do Gemini.

**8. `llm/*`.** `LLMClient` tem 2 métodos (`generate`, `generate_structured`). `GeminiClient` usa `google-genai` com
`automatic_function_calling` desligado (quem executa somos nós), timeout e `call_with_retries` (429/5xx/timeout, backoff
exponencial com jitter; 401/403/400 não repetem). `to_contents` converte o histórico neutro e reaproveita o conteúdo bruto
do modelo (preserva *thought signatures*).

**9. `agent.py`.** `chat()`: valida tamanho → rate limit → grava mensagem → modo real (`_run_llm`) ou demo (`_run_demo`).
Loop: modelo responde → se pediu ferramentas, executamos e devolvemos os resultados (sem campos só-de-UI) → repete até
texto final ou `max_tool_steps`. Erros do provedor viram mensagem amigável e o turno incompleto é descartado.

**10. `planner.py` (modo demo).** Acha a **primeira** palavra de intenção na frase (delete/update/list/complete/reminder/
task/email) — por isso "Crie uma tarefa para *editar* o documento" cria tarefa. Extrai título, prioridade, data, destinatário.
Frases sem intenção e sem cara de pergunta → pedido de esclarecimento.

**11. `api.py` / `ui.py` / `render.py`.** A API é uma casca fina (`X-Session-Id`, códigos de erro estáveis, `DELETE` exige
`confirm=true`). A UI Gradio liga eventos às mesmas funções; `deliver_due` (timer de 20 s) exibe o aviso **e depois** marca
`notificado`. `render.py` escapa todo texto (`html.escape`).

**12. `evals/`.** `scenarios.json` (53) + `run_eval.py`: roda o roteador (ou o Gemini), compara ferramenta/argumentos/RAG e
calcula taxas com intervalo de Wilson.

## Parte 2 — Explicação de 2 minutos (para a entrevista)

> "O Lily Tasks é um assistente de produtividade. O usuário conversa; o modelo decide chamar ferramentas (criar tarefa,
> lembrete, rascunho de e-mail, buscar nos documentos). O ponto central do projeto é que **o LLM é tratado como não
> confiável**: os argumentos são validados com Pydantic; exclusões só acontecem depois de uma confirmação que o modelo não
> controla; textos recuperados de documentos são limpos e, se parecerem um ataque, bloqueiam escritas naquele turno;
> datas são resolvidas por código; e o RAG sabe dizer 'não encontrei'. Tudo isso fica atrás de uma interface de LLM de
> dois métodos, então os testes usam um LLM falso e rodam sem rede. Medi o comportamento com 53 cenários e reporto
> intervalos de confiança — e deixei casos difíceis falhando de propósito para mostrar os limites."

## Parte 3 — Perguntas de entrevista (com respostas-guia)

1. **Por que não deixar o LLM calcular as datas?** Modelos erram aritmética de calendário e fuso; o servidor tem o relógio
   e o fuso corretos. O modelo só repassa a frase; o código resolve e é testável.
2. **Como você impede que o modelo apague dados?** A ferramenta sensível não executa: grava ação pendente e devolve token.
   Só o clique do usuário (token da mesma sessão, uso único, expira) executa. Mesmo um modelo "convencido" não consegue.
3. **O que é prompt injection indireta e como você mitiga?** Instruções escondidas em conteúdo recuperado. Camadas: filtrar
   linhas suspeitas; marcar como dado não confiável; bloquear escrita no turno; confirmação externa; prompt de sistema.
   Admito que a detecção por regras é incompleta — por isso as camadas que não dependem dela.
4. **Por que BM25 e não embeddings?** Corpus pequeno, CPU, sem download, explicável e determinístico. Troco quando houver
   sinônimos/volume (exemplo real: "bolsa de estudos" falha). Híbrido (BM25 + vetor) é a evolução natural.
5. **Como o RAG decide que não sabe?** Cobertura ponderada por idf do melhor trecho + score mínimo. Termos fora do corpus
   pesam como raros e derrubam a cobertura. Limiares são heurísticos — validar com um conjunto separado.
6. **Como você trata 429 e timeouts?** Classificação de erros em `LLMError`; retry com backoff exponencial + jitter só para
   transitórios; teto de tentativas; erro vira mensagem clara; o turno incompleto não corrompe o histórico.
7. **Como evita vazamento entre usuários?** `session_id` em todas as consultas, chaves compostas, pendências escopadas,
   testes de isolamento, TTL. Limite: o ID é o único segredo (sem login).
8. **Qual a diferença entre teste determinístico e avaliação de LLM?** Primeiro: regressão do código, reprodutível.
   Segundo: mede o modelo, varia entre execuções; precisa de conjunto separado e intervalos de confiança.
9. **Seus 100% significam que é bom?** Não: regras e cenários nasceram juntos (conjunto de desenvolvimento). Por isso
   mostro IC, mantenho casos difíceis e proponho *holdout* escrito por outra pessoa.
10. **Por que `extra="forbid"`?** O modelo não pode introduzir parâmetros não previstos (ex.: `admin=true`).
11. **Por que desligar o *automatic function calling*?** Para controlar validação, confirmação, logs e limites no meu código.
12. **O que são *thought signatures*?** Em modelos Gemini com raciocínio, o conteúdo do modelo traz assinaturas que devem ser
    devolvidas no próximo turno com chamadas de função; por isso guardo o conteúdo bruto no histórico em memória.
13. **Como diferencia lembrete registrado de notificação?** Estado calculado; `notified_at` só é gravado depois que a UI
    exibiu o aviso. Sem scheduler/push, nunca digo "enviei".
14. **Como escalaria?** Postgres, fila/worker para lembretes (e canais reais), autenticação, rate limit distribuído,
    cache de conversas fora da memória, observabilidade (traces) e avaliação contínua com amostras reais anonimizadas.
15. **O que você faria com mais tempo?** Avaliação `llm` com 3 execuções e holdout; RAG híbrido; streaming; testes
    adversariais de injeção contra o modelo real; internacionalização do parser de datas.

## Parte 4 — Exercícios (do mais fácil ao mais difícil)

1. **Adicionar um documento** em `data/docs/` e 3 cenários RAG para ele. Rode a avaliação e `build_static.py`.
2. **Nova prioridade "urgente"**: altere `Priority`, `normalize_priority`, a UI e os testes.
3. **Corrigir o `EML-04`**: faça o planner priorizar e-mail quando "e-mail" aparece logo após "preciso de um". Não quebre os outros cenários.
4. **Expandir datas**: suporte a "daqui a 1 mês", "fim do mês" e "próxima semana". Escreva primeiro os testes.
5. **Nova ferramenta `snooze_reminder`** (adiar em N minutos): schema, handler, declaração, teste de validação, cenário.
6. **Editar rascunho via chat** ("deixe o e-mail mais curto") usando `generate_structured` no modo real.
7. **Trocar o BM25 por busca híbrida** mantendo `RetrievalResult` (pode usar um modelo de embedding pequeno local); compare no `RAG-11`.
8. **Holdout de avaliação**: peça a um colega 30 frases novas, avalie sem alterar regras e compare com o conjunto atual.
9. **Teste adversarial**: escreva 10 variações de injeção (inclusive em inglês e com tags falsas) e meça quantas o `guard` pega; melhore e **documente os falsos positivos**.
10. **Persistir contexto do modelo** (hoje em memória) no SQLite, sem armazenar o conteúdo bruto proprietário — decida e justifique o que guardar.

## Parte 5 — Armadilhas que você deve saber explicar

- O stub/falta de rede: esta entrega **não** rodou FastAPI, Gradio, Gemini, pytest e ruff; diga isso com naturalidade e mostre como validar.
- A camada gratuita do Gemini tem limites e política de dados próprias; o nome do modelo muda com o tempo (por isso `GEMINI_MODEL`).
- `localStorage`/Static Space isola por navegador, não por "conta".
