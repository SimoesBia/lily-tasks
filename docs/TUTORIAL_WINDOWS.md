# Tutorial — do zero à publicação (Windows 11, custo zero)

Use o **PowerShell**. Onde houver `SEU-USUARIO`, troque pelo seu usuário (GitHub / Hugging Face).

## 1. Instalar o que falta

1. **Python 3.12**: python.org/downloads → marque **"Add python.exe to PATH"** → Install. Teste: `py --version`.
2. **Git**: git-scm.com/download/win (opções padrão). Teste: `git --version`.
3. **VS Code** (opcional): code.visualstudio.com, com a extensão *Python*.

## 2. Preparar o projeto

```powershell
cd $HOME\Documents
# descompacte o ZIP aqui (ex.: Documentos\lily-tasks) e entre na pasta
cd lily-tasks
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```
Se aparecer erro de "execução de scripts desabilitada": `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, responda `S`
e rode o `Activate.ps1` de novo. O prompt deve mostrar `(.venv)`.

```powershell
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

## 3. Chave gratuita do Gemini (opcional — sem ela o app roda em modo demo)

1. Acesse **aistudio.google.com/apikey** com sua conta Google → **Create API key** (não pede cartão).
2. No AI Studio confira qual modelo *Flash* está na camada gratuita e anote o nome.
3. Crie o arquivo `.env`:
   ```powershell
   copy .env.example .env
   notepad .env
   ```
   Preencha `GEMINI_API_KEY=` (sem aspas, sem espaços) e, se o modelo padrão não existir para você, `GEMINI_MODEL=<nome>`.
4. **Nunca** cole a chave em código, README, prints ou mensagens. O `.env` já está no `.gitignore`.

## 4. Executar localmente

```powershell
python app.py
```
Abra **http://127.0.0.1:7860**. O selo no topo diz o modo: *"IA real · Gemini"* ou *"Demonstração simulada"*.
Teste: "Crie uma tarefa para enviar o relatório amanhã às 9h com prioridade alta" → o painel **Tarefas** deve atualizar.
Para encerrar: `Ctrl+C`. Para forçar o modo demo mesmo com chave: `$env:LILY_FORCE_DEMO="1"; python app.py`.

API (opcional): `uvicorn lily.api:create_app --factory --reload` → http://127.0.0.1:8000/docs

## 5. Testes, lint e avaliação

```powershell
pytest                                            # 67 testes
ruff check .                                      # lint (use "ruff check --fix ." para correções simples)
python -m evals.run_eval --mode deterministic     # métricas reais -> evals/results/
python -m evals.run_eval --mode llm --delay 6     # com Gemini real (usa sua cota)
```
**Se algo falhar, não é você:** esta entrega foi escrita sem poder executar `pytest`, `ruff`, FastAPI, Gradio nem o Gemini
(ver README → "Estado de validação"). Cole o erro completo, corrija e rode de novo — é um ótimo exercício de depuração.

## 6. GitHub

1. Em github.com → **New repository** → nome `lily-tasks`, **Public**, **sem** README/.gitignore/licença (o projeto já tem).
2. No PowerShell, na pasta do projeto:
   ```powershell
   git init -b main
   git add .
   git status                       # CONFIRA: .env e *.sqlite3 NÃO podem aparecer
   git commit -m "Lily Tasks: versão inicial"
   git remote add origin https://github.com/SEU-USUARIO/lily-tasks.git
   git push -u origin main
   ```
   (O login abre no navegador pelo Git Credential Manager.)
3. Verifique no site: a aba **Actions** deve rodar o CI (lint, testes, avaliação).
4. Se o CI falhar, abra o log, corrija localmente e faça novo `git push`.
5. Adicione ao repositório o **tópico** `ai-engineering`, `llm`, `rag`, `fastapi` e fixe-o no seu perfil.

## 7. Hugging Face

1. Crie conta em huggingface.co. Em **Settings → Access Tokens** crie um token com permissão **Write** (guarde-o como senha).
2. **Space estático (sempre grátis):**
   ```powershell
   python scripts\build_static.py
   ```
   Em huggingface.co/new-space: nome `lily-tasks-static`, **SDK: Static**. Depois:
   ```powershell
   cd $HOME\Documents
   git clone https://huggingface.co/spaces/SEU-USUARIO/lily-tasks-static
   copy lily-tasks\static_space\index.html lily-tasks-static\
   copy lily-tasks\static_space\README.md  lily-tasks-static\    # sobrescreva
   cd lily-tasks-static
   git add . ; git commit -m "demo estática" ; git push      # usuário = SEU-USUARIO, senha = o token
   ```
3. **Gradio Space (se a sua conta permitir grátis):** em new-space escolha **SDK: Gradio**, hardware **CPU basic**.
   Confira se está marcado como gratuito; se pedir pagamento, **pare** e fique só com o estático.
   ```powershell
   cd $HOME\Documents\lily-tasks
   git remote add space https://huggingface.co/spaces/SEU-USUARIO/lily-tasks
   git push space main --force      # o Space nasce com um commit inicial próprio; --force só na primeira vez
   ```
   Acompanhe a aba **Logs** até "Running". Se o build falhar por versão do Gradio, veja DEPLOYMENT.md.
4. Teste em janela anônima (roteiro em DEPLOYMENT.md). Troque `SEU-USUARIO` nos links do README e dê novo push.

## 8. Atualizar depois

```powershell
git add . ; git commit -m "o que mudou" ; git push origin main ; git push space main
```
(Estático: `python scripts\build_static.py`, copie os arquivos e faça push no repositório do Space estático.)

## 9. LinkedIn e currículo

**Currículo (seção Projetos):**
> **Lily Tasks — assistente de produtividade com IA** (Python, FastAPI, Gemini API, RAG, SQLite) · github.com/SEU-USUARIO/lily-tasks
> - Agente com *tool calling* e validação estrita (Pydantic); exclusões exigem confirmação fora do LLM.
> - RAG com BM25 e referências a fontes; abstenção quando não há evidência; defesa em camadas contra *prompt injection*.
> - 53 cenários de avaliação reproduzíveis com intervalos de confiança; CI no GitHub Actions; deploy gratuito no Hugging Face.

**Post no LinkedIn (rascunho):**
> Construí o Lily Tasks, um assistente de produtividade com IA, para estudar o que fica *ao redor* do LLM: validação de
> ferramentas, segurança contra prompt injection, tratamento de falhas e avaliação. Aprendi que o mais difícil não foi
> chamar o modelo, e sim garantir que ele não faça o que não deve — e medir isso sem inventar números. Código e demo: [links].
> Feedback é bem-vindo! #AIEngineering #LLM #RAG #Python

Só publique números que você mesmo rodou. Se citar métricas do modo `llm`, rode-o antes.
