# Publicação (custo zero)

Duas opções independentes. **Não presumo** que sua conta tenha Gradio Space gratuito: confira na tela de criação do Space
(o hardware "CPU basic" costuma ser gratuito, mas as regras do Hugging Face podem mudar). Se não aparecer como gratuito,
publique só a versão estática.

## Opção A — Gradio Space (modo demo público + IA real opcional)

1. Crie o Space em huggingface.co/new-space: **SDK = Gradio**, hardware **CPU basic**, visibilidade pública.
2. O `README.md` da raiz já traz o cabeçalho que o Space exige (`sdk: gradio`, `app_file: app.py`). Não fixei
   `sdk_version`: o Space usa a versão atual do Gradio. Se o build quebrar por incompatibilidade, rode `pip show gradio`
   no seu ambiente local que funcionou e acrescente `sdk_version: <essa versão>` ao cabeçalho.
3. Envie o código (veja o [tutorial](docs/TUTORIAL_WINDOWS.md) para o `git push`). O Hugging Face instala `requirements.txt`.
4. **Modo do Space público:** o HF define `SPACE_ID`, o que ativa automaticamente sessões isoladas por visitante, TTL de
   limpeza e **ignora** a chave do servidor. Visitantes veem o *modo demonstração simulada* e, se quiserem, colam a
   **própria** chave do Gemini (usada só naquela chamada).
5. (Opcional, gasta SUA cota) para IA real para todos: *Settings → Variables and secrets* → secret `GEMINI_API_KEY` e
   variável `LILY_ALLOW_SHARED_KEY=1`. O limite de mensagens por minuto por sessão protege a cota, mas não é infalível.
6. Armazenamento do Space é efêmero: o SQLite some ao reiniciar — ok para demo (dados são temporários por desenho).

## Opção B — Static Space (sem Python, sem chave)

1. `python scripts/build_static.py` (regenera `static_space/index.html` a partir de `data/docs/`).
2. Crie outro Space com **SDK = Static**.
3. Envie para ele **o conteúdo da pasta `static_space/`** (`index.html` e `README.md`, este já com `sdk: static`).
   Ignore `template.html` (pode enviar, mas não é necessário).
4. Funciona 100% no navegador; os dados ficam no `localStorage` de cada visitante. Nenhuma chave existe nessa versão.

## Testar a demonstração pública

- Abra o Space em janela anônima: deve aparecer o selo **"Demonstração simulada"**.
- "Crie uma tarefa para enviar o relatório amanhã às 9h" → painel de tarefas atualiza.
- "Apague a tarefa 1" → deve pedir **Confirmar/Cancelar**.
- "Existe algum aviso importante nos benefícios?" → o FAQ contém uma instrução maliciosa de propósito; a resposta deve trazer o aviso ⚠ de que ela foi removida e **nenhuma tarefa deve ser apagada**.
- Abra outra janela anônima: não deve ver as tarefas da primeira.
- Inspecione o repositório e os *logs* do Space: nenhuma chave aparece.

## Atualizar a publicação

```powershell
git add . ; git commit -m "descrição" ; git push origin main ; git push space main
```
Na versão estática, rode `python scripts/build_static.py`, copie `static_space/` para o repositório do Space estático e faça push.
