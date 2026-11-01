# API REST

Execução: `uvicorn lily.api:create_app --factory --reload` → documentação interativa em **/docs** (Swagger) e **/redoc**.

Toda rota (exceto `/health`, `/sessions` e `/rag/search`) exige o cabeçalho `X-Session-Id` (16–64 caracteres `A-Za-z0-9_-`).
Cada ID enxerga **apenas** os próprios dados. A chave do Gemini vem do ambiente do servidor; nunca trafega pela API.

| Método e rota | Descrição | Erros comuns |
|---|---|---|
| `GET /health` | Estado, versão e modo (`real`/`demo`) | — |
| `POST /sessions` | Cria sessão → `{session_id}` | — |
| `PUT /session/timezone` | `{timezone}` (ex.: `America/Recife`) | 422 fuso inválido |
| `DELETE /session` | Apaga todos os dados da sessão | — |
| `POST /chat` | `{message}` → `{reply, mode, tool_events, pending_action, error}` | 422, 429 |
| `POST /actions/{token}/confirm` · `/cancel` | Confirma/cancela ação sensível pendente | `not_found` |
| `GET /history` · `GET /activity` | Histórico e log de ferramentas (só metadados) | — |
| `GET /tasks?status=&priority=&due_before=&q=` | Lista com filtros | — |
| `POST /tasks` | `{title, due?, priority?, notes?}` | 422, 409 limite |
| `PATCH /tasks/{ref}` | `{title?, due?, clear_due?, priority?, notes?}` — `ref` = número ou trecho do título | 404, 409 ambíguo |
| `POST /tasks/{ref}/complete` | Conclui | 409 já concluída |
| `DELETE /tasks/{ref}?confirm=true` | Exclui; sem `confirm=true` → **428** | 428, 404 |
| `GET/POST /reminders` · `PATCH/DELETE /reminders/{ref}` | CRUD de lembretes (`DELETE` também exige `confirm=true`) | `past_date`, `invalid_date` |
| `GET /notifications/due` | Vencidos e **não notificados** (consultar não marca) | — |
| `POST /notifications/{ref}/ack` | O cliente confirma que **exibiu** o aviso → `state: notificado` | — |
| `GET /drafts` · `PATCH /drafts/{seq}` | Lista e edita rascunhos de e-mail (não há envio) | 404 |
| `POST /rag/search` | `{query}` → `{sufficient, coverage, passages[{source,text,score}]}` | — |

Formato de erro: `{"ok": false, "error": "<codigo>", "message": "...", "candidates": [...]}`. Códigos:
`not_found` 404 · `ambiguous` 409 · `invalid_arguments`/`invalid_date`/`invalid_session` 422 ·
`confirmation_required` 428 · `rate_limited` 429 · `limit_reached` 409.

Exemplo:

```powershell
$sid = (Invoke-RestMethod -Method Post http://127.0.0.1:8000/sessions).session_id
Invoke-RestMethod -Method Post http://127.0.0.1:8000/tasks -Headers @{"X-Session-Id"=$sid} `
  -ContentType "application/json" -Body '{"title":"Enviar relatório","due":"amanhã às 9h","priority":"alta"}'
```
