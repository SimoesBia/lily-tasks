---
title: Lily Tasks
emoji: 🪻
colorFrom: purple
colorTo: green
sdk: gradio
app_file: app.py
pinned: false
license: mit
short_description: Assistente de produtividade com IA, Python e RAG
---

# 🪻 Lily Tasks — AI Productivity Assistant

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![AI Engineering](https://img.shields.io/badge/AI-Engineering-8B5CF6?style=flat)
![LLM](https://img.shields.io/badge/LLM-Integration-6366F1?style=flat)
![RAG](https://img.shields.io/badge/RAG-BM25-D946EF?style=flat)
![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat)

## Sobre o projeto

A **Lily Tasks** é uma assistente virtual de produtividade desenvolvida em Python, com integração de inteligência artificial para ajudar na organização de tarefas, lembretes e informações.

O projeto foi criado com o objetivo de explorar, na prática, o desenvolvimento de aplicações com modelos de linguagem (LLMs), integrando funcionalidades de gerenciamento de tarefas, consultas a documentos e automação de ações.

Além da interação por chat, a aplicação possui uma interface visual para acompanhar as informações cadastradas.

O desenvolvimento também aborda conceitos importantes de engenharia de software, como organização de código, validação de dados, tratamento de erros e segurança.

## Funcionalidades

- **Chat com IA:** interação em português para interpretar solicitações e executar ações.
- **Gerenciamento de tarefas:** criação, consulta, edição, conclusão e exclusão de tarefas.
- **Lembretes:** cadastro de lembretes com datas e horários, incluindo expressões como "amanhã às 14h".
- **Rascunhos de e-mail:** geração de textos que podem ser revisados e copiados pelo usuário, sem envio automático.
- **Consulta a documentos (RAG):** busca de informações em documentos de exemplo, com indicação das fontes utilizadas.
- **Painel de produtividade:** visualização de tarefas, lembretes e outras informações.
- **Modo demonstração:** permite explorar funcionalidades básicas sem configurar uma chave de API.

## Tecnologias utilizadas

| Tecnologia | Aplicação no projeto |
|---|---|
| Python | Linguagem principal |
| FastAPI | Desenvolvimento da API |
| Gradio | Interface web interativa |
| Gemini API | Integração com modelo de linguagem |
| Pydantic | Validação de dados |
| SQLite | Armazenamento local |
| BM25 | Busca de informações nos documentos |
| Pytest | Testes automatizados |
| Ruff | Análise e padronização do código |
| Git e GitHub | Versionamento do projeto |

## Como a Lily funciona

A aplicação recebe uma solicitação do usuário e identifica como ela deve ser processada.

Dependendo do pedido, a Lily pode consultar informações, utilizar ferramentas internas ou realizar operações relacionadas às tarefas e aos lembretes.

**Fluxo simplificado:**

1. O usuário envia uma mensagem pela interface.
2. A aplicação interpreta a solicitação com auxílio do modelo de linguagem ou das regras do modo demonstração.
3. Quando necessário, uma ferramenta interna executa a operação.
4. As informações são consultadas ou armazenadas no banco de dados.
5. A Lily apresenta o resultado ao usuário.

Para perguntas sobre documentos, o projeto utiliza **RAG (Retrieval-Augmented Generation)**, uma técnica que permite recuperar informações de uma base de documentos para auxiliar na elaboração de respostas.

A busca utiliza o algoritmo BM25, que identifica trechos relevantes com base nos termos da consulta.

## Organização do projeto

O código foi dividido em módulos para facilitar a manutenção e a compreensão das responsabilidades de cada componente.

```text
lily-tasks/
├── app.py
├── lily/
│   ├── llm/
│   ├── rag/
│   └── services/
├── data/
│   └── docs/
├── evals/
├── tests/
├── docs/
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

- **lily/** — lógica principal da aplicação.
- **llm/** — comunicação com o modelo de linguagem.
- **rag/** — recuperação de informações em documentos.
- **services/** — operações relacionadas às funcionalidades.
- **data/docs/** — documentos fictícios utilizados nas consultas.
- **evals/** — cenários para avaliação de comportamentos.
- **tests/** — testes automatizados.
- **docs/** — documentação complementar.

## Como executar localmente

### Pré-requisitos

- Python compatível com as dependências do projeto.
- Git.
- Chave da API do Gemini para utilizar o modo com LLM.

### Instalação

**1. Clone o repositório:**

```bash
git clone https://github.com/SimoesBia/lily-tasks.git
cd lily-tasks
```

**2. Crie um ambiente virtual:**

```powershell
py -3.12 -m venv .venv
```

**3. Ative o ambiente virtual no PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**4. Instale as dependências:**

```powershell
python -m pip install -r requirements.txt
```

**5. Inicie a aplicação:**

```powershell
python app.py
```

A interface local utiliza o endereço:

http://127.0.0.1:7860

### Configuração da IA

Para utilizar a integração com Gemini, crie um arquivo `.env` a partir do `.env.example` e configure a variável:

```env
GEMINI_API_KEY=sua_chave_aqui
```

Sem a chave, a aplicação oferece um modo de demonstração baseado em regras.

## Cuidados e limitações

A Lily Tasks é um projeto demonstrativo, desenvolvido para estudo e aplicação prática de conceitos de inteligência artificial e engenharia de software.

Algumas características importantes:

- Os documentos utilizados na demonstração são fictícios.
- Os rascunhos de e-mail não são enviados automaticamente.
- Os lembretes não utilizam notificações externas ou push.
- A busca BM25 depende da correspondência entre os termos da consulta e os documentos.
- Ações sensíveis, como exclusões, utilizam mecanismos de confirmação.

O projeto também inclui documentação sobre arquitetura e segurança:

- [Arquitetura](ARCHITECTURE.md)
- [Segurança](SECURITY.md)
- [Guia de execução no Windows](docs/TUTORIAL_WINDOWS.md)

## Aprendizados

O desenvolvimento da Lily Tasks permite aplicar e aprofundar conhecimentos em:

- Integração de APIs e modelos de linguagem.
- Desenvolvimento de aplicações com Python.
- Organização de projetos em módulos.
- Manipulação e persistência de dados.
- Recuperação de informações com RAG.
- Validação de entradas e tratamento de erros.
- Desenvolvimento de interfaces e APIs.
- Versionamento e documentação de software.

## Licença

Este projeto está disponível sob a [Licença MIT](LICENSE).
