# Segurança

## Modelo de ameaça (resumido)

| Ameaça | Mitigação | Onde |
|---|---|---|
| Chave de API vazar | `.env` no `.gitignore`; chave só do ambiente; logs redigem `AIza…`; a API nunca recebe/devolve chaves; chave do visitante (opcional) só em memória | `config.py`, `logging_utils.py`, `runtime.py` |
| Space público gastar a SUA cota | Chave do servidor **ignorada** em Space público, salvo `LILY_ALLOW_SHARED_KEY=1`; limite de mensagens/min por sessão | `Settings.env_llm_enabled`, `agent.RateLimiter` |
| Execução arbitrária | Não há ferramenta de código/shell/rede; cada ferramenta chama um serviço fixo; nome desconhecido é recusado | `tools.py` |
| Argumentos maliciosos/inventados | Pydantic estrito; SQL sempre parametrizado; HTML sempre escapado (`render.esc`) | `schemas.py`, `services/*`, `render.py` |
| Exclusão induzida | Ferramentas sensíveis só criam ação pendente; execução exige token de uso único da **mesma sessão**, expira em 10 min | `tools.py`, `db.take_pending` |
| Prompt injection em documentos | (1) remoção de linhas suspeitas; (2) resultado marcado `untrusted_content`; (3) escrita bloqueada no turno; (4) confirmação fora do LLM; (5) system prompt manda tratar dados como dados | `rag/guard.py`, `tools.py`, `agent.py` |
| Vazamento entre visitantes | `session_id` em todas as tabelas e consultas; testes de isolamento; TTL de limpeza | `db.py`, `tests/` |
| Abuso/negação de serviço | Tamanho máximo de mensagem, rate limit, limite de itens por sessão, passos de ferramenta limitados, timeouts | `config.py`, `agent.py` |
| Dados sensíveis em logs | Só metadados (ferramenta/status/código de erro); erros de validação não ecoam o valor digitado | `db.log_tool`, `tools.execute` |

## O que **não** é garantido

- A detecção de injeção é por regras (lista finita): um ataque bem escrito pode passar. Por isso existem as camadas 3–5,
  que não dependem de reconhecer o ataque.
- Sessões são identificadas por um ID aleatório no navegador; quem tem o ID acessa a sessão (não há login).
- Em modo real, o texto das conversas é enviado ao Gemini. **Na camada gratuita o Google pode usar dados para
  melhorar seus produtos** (confira os termos vigentes). Não envie dados pessoais ou confidenciais.
- A chave colada no campo "usar minha chave" trafega até o servidor do Space para a chamada ao Gemini; ela não é gravada
  nem logada, mas confie apenas em Spaces cujo código você leu — ou rode localmente.

## Checklist antes de publicar

- [ ] `git ls-files | findstr /i ".env sqlite"` não lista `.env` nem bancos.
- [ ] `git log -p | findstr AIza` não encontra nenhuma chave (se encontrar: **revogue a chave** no AI Studio).
- [ ] No Space, nenhum *secret* `GEMINI_API_KEY` definido (a menos que queira o modo real compartilhado).
- [ ] `LILY_PUBLIC=1` (ou `SPACE_ID`, que o Hugging Face define sozinho) ativa sessões isoladas por visitante.
