# 🪻 Lily Tasks — AI Productivity Assistant

**Assistente de produtividade com Python, FastAPI, Gradio, integração com LLMs e recuperação de informações com RAG.**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Gradio](https://img.shields.io/badge/Interface-Gradio-F97316?style=flat)
![AI Engineering](https://img.shields.io/badge/AI-Engineering-8B5CF6?style=flat)
![RAG](https://img.shields.io/badge/RAG-BM25-D946EF?style=flat)
![Tests](https://img.shields.io/badge/Tests-Pytest-22C55E?style=flat)
![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat)

## 🌐 Demonstração online

### [🪻 Experimentar a Lily Tasks no Hugging Face](https://huggingface.co/spaces/SimoesBia/lily-tasks-demo)

A Lily Tasks possui uma demonstração pública que permite experimentar funcionalidades de produtividade diretamente pelo navegador, sem instalação ou configuração de chave de API.

**Importante:** a demonstração hospedada no Hugging Face é uma versão estática, construída com HTML e JavaScript. Ela utiliza regras determinísticas para simular interações, sem executar o backend Python ou realizar chamadas a modelos de linguagem.

As informações são armazenadas no `localStorage` do navegador, permitindo preservar os dados após atualizar a página. Esse armazenamento é local ao navegador e não representa sincronização entre dispositivos.

A aplicação Python completa, disponível neste repositório, utiliza FastAPI, Gradio, SQLite, recuperação de documentos com BM25 e integração opcional com Gemini.

## 📖 Sobre o projeto

A **Lily Tasks** é um projeto de assistente virtual de produtividade desenvolvido para explorar conceitos de inteligência artificial, engenharia de software e desenvolvimento de aplicações Python.

Seu objetivo é permitir que usuários interajam por meio de comandos em linguagem natural para organizar tarefas, cadastrar lembretes, elaborar rascunhos de e-mail e consultar documentos.

Além do chat, a aplicação oferece uma interface visual para acompanhar as informações cadastradas.

O projeto também foi utilizado para estudar e aplicar conceitos como:

- Integração com modelos de linguagem (LLMs).
- Execução de ferramentas a partir de solicitações do usuário.
- Desenvolvimento de APIs e interfaces.
- Persistência de dados.
- Recuperação de informações com RAG.
- Validação de entradas e tratamento de erros.
- Testes automatizados e prevenção de regressões.
- Segurança e documentação técnica.

A Lily Tasks é um projeto de aprendizado e demonstração, não um produto comercial.

## ✨ Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| Chat em português | Interpretação de solicitações no modo com LLM ou por regras no modo demonstração |
| Gerenciamento de tarefas | Criação, consulta, edição, conclusão e exclusão |
| Prioridades e prazos | Organização de tarefas por prioridade e data |
| Lembretes | Cadastro com datas e horários, incluindo expressões em linguagem natural |
| Rascunhos de e-mail | Preparação de textos para revisão e cópia, sem envio automático |
| Consulta a documentos | Recuperação de informações em documentos fictícios usando BM25 |
| Painel visual | Acompanhamento de tarefas e lembretes |
| Modo demonstração | Execução de funcionalidades básicas sem chave de API |
| Integração opcional com Gemini | Utilização de um modelo de linguagem para interpretação de solicitações |

## 🛠️ Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python | Linguagem principal da aplicação |
| FastAPI | Desenvolvimento da API |
| Gradio | Interface web da aplicação Python |
| Gemini API | Integração opcional com modelo de linguagem |
| Pydantic | Validação de dados |
| SQLite | Persistência local |
| BM25 | Recuperação de informações em documentos |
| Pytest | Testes automatizados |
| Ruff | Ferramenta de análise estática e padronização |
| HTML, CSS e JavaScript | Demonstração estática publicada no Hugging Face |
| Git e GitHub | Versionamento e publicação do código |
| Hugging Face Spaces | Hospedagem da demonstração pública |

## 🧠 Como a Lily funciona

A aplicação recebe uma mensagem e identifica como a solicitação deve ser processada.

O processamento depende do modo utilizado.

### Modo demonstração

Utiliza regras determinísticas para interpretar comandos e executar operações suportadas.

Esse modo não utiliza um modelo de linguagem. Seu objetivo é permitir testes previsíveis sem depender de uma API externa.

### Modo com LLM

Utiliza a integração configurada com Gemini para interpretar solicitações e selecionar ferramentas disponíveis na aplicação.

A execução das operações continua sendo responsabilidade das ferramentas internas, com validações e tratamento de erros.

### Fluxo simplificado

1. O usuário envia uma mensagem pela interface.
2. A aplicação interpreta a solicitação usando regras ou o modelo de linguagem configurado.
3. Quando necessário, uma ferramenta interna executa a operação.
4. Os dados são consultados ou armazenados.
5. A Lily apresenta o resultado ao usuário.

### Recuperação de informações com RAG

Para responder a perguntas sobre documentos, o projeto utiliza conceitos de **Retrieval-Augmented Generation (RAG)**.

A etapa de recuperação utiliza BM25, um algoritmo de busca lexical que identifica documentos ou trechos relevantes com base nos termos da consulta.

As informações recuperadas podem ser utilizadas como contexto para a elaboração das respostas no modo com modelo de linguagem.

A base documental é composta por informações fictícias, utilizadas exclusivamente para demonstração e testes.

## 📁 Estrutura do projeto

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
├── scripts/
├── static_space/
├── ARCHITECTURE.md
├── DEPLOYMENT.md
├── EVALUATION.md
├── SECURITY.md
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── README.md
```

**Principais diretórios:**

- `lily/`: lógica principal e componentes da aplicação.
- `lily/llm/`: comunicação com o modelo de linguagem.
- `lily/rag/`: recuperação de informações em documentos.
- `lily/services/`: serviços relacionados às funcionalidades.
- `data/docs/`: documentos fictícios utilizados na recuperação.
- `evals/`: cenários e ferramentas de avaliação.
- `tests/`: testes automatizados.
- `docs/`: documentação complementar.
- `scripts/`: scripts auxiliares.
- `static_space/`: arquivos da demonstração estática.

## 🧪 Testes, depuração e validação

Durante o desenvolvimento, foram realizados testes manuais e automatizados para verificar funcionalidades, identificar comportamentos inesperados e validar correções.

Uma das prioridades foi transformar problemas encontrados durante o uso da aplicação em cenários reproduzíveis, que pudessem ser verificados novamente após alterações no código.

### Testes automatizados

O projeto utiliza Pytest para verificar comportamentos da aplicação.

Entre os testes relacionados às correções estão:

- `tests/test_demo_regressions.py`: cenários de regressão do modo demonstração.
- `tests/test_planner_pending.py`: comportamentos relacionados ao tratamento de solicitações com contexto pendente.

Para executar os testes:

```bash
python -m pytest -q
```

Na última validação local realizada durante o desenvolvimento, a suíte Pytest foi executada com todos os testes aprovados.

Esse resultado corresponde à execução local observada e não representa uma garantia de ausência de falhas em todos os cenários possíveis.

### Avaliação de comportamentos

Além dos testes automatizados, o projeto possui uma estrutura de avaliação de cenários relacionados a:

- Extração de informações de comandos.
- Seleção de ferramentas.
- Recuperação de documentos.
- Tratamento de ambiguidades.
- Segurança e identificação de instruções maliciosas em conteúdo recuperado.

O modo determinístico pode ser avaliado com:

```bash
python -m evals.run_eval --mode deterministic --min-pass 0.90
```

**Resultados registrados na avaliação determinística de 01/11/2026:**

| Métrica | Resultado |
|---|---|
| Cenários gerais | 51/53 — 96,2% |
| Cenários sem os dois casos difíceis conhecidos | 51/51 — 100% |
| Seleção de ferramenta | 52/53 — 98,1% |
| Extração de argumentos | 25/25 — 100% |
| Recuperação de fonte no top-1/top-3 | 8/8 em ambos |
| Abstenção correta no RAG | 3/3 |

Esses números são referentes ao conjunto de avaliação documentado e não devem ser interpretados como uma medida geral da qualidade da IA.

Os cenários determinísticos foram utilizados durante o desenvolvimento e ajustes do sistema. Uma avaliação mais robusta exigiria também novos cenários independentes, não utilizados para orientar as correções.

A avaliação do modelo Gemini real é uma etapa separada e não deve ser confundida com os resultados do modo determinístico.

Os detalhes, limitações e comandos estão disponíveis em [EVALUATION.md](EVALUATION.md).

## 🔧 Desafios técnicos, erros e correções

O desenvolvimento da Lily Tasks envolveu ciclos de implementação, experimentação, identificação de falhas e ajustes.

Alguns dos problemas encontrados foram especialmente importantes para compreender melhor o funcionamento de sistemas que interpretam comandos e executam ações.

### 1. Interpretação incorreta de comandos de edição

**Problema**

Durante os testes manuais, uma solicitação como:

> Altere a prioridade da tarefa 1 para média.

Nem sempre era interpretada corretamente.

Em determinadas situações, a assistente solicitava esclarecimentos desnecessários ou interpretava a resposta seguinte como uma nova operação.

Um dos comportamentos observados foi a criação indevida de uma tarefa quando o usuário estava apenas tentando identificar qual tarefa deveria ser modificada.

**Correção**

Foram realizados ajustes na interpretação de comandos e no tratamento de solicitações que dependem de esclarecimentos.

**Validação**

O comando anteriormente problemático foi executado novamente após as correções, e a alteração de prioridade foi concluída corretamente.

Também foram incorporados testes de regressão relacionados a esse comportamento.

**Aprendizado**

Esse problema evidenciou a importância de preservar o contexto das interações, distinguir comandos novos de respostas de esclarecimento e verificar os efeitos reais das ações executadas.

### 2. Tratamento de contexto pendente

**Problema**

Quando uma solicitação não continha todas as informações necessárias, a aplicação precisava solicitar um esclarecimento.

O desafio era garantir que a resposta do usuário fosse associada à solicitação original, em vez de ser interpretada isoladamente.

**Correção**

Foram realizados ajustes no tratamento das interações com informações pendentes.

**Validação**

Foram adicionados cenários automatizados para verificar comportamentos relacionados a esse fluxo.

**Aprendizado**

Em interfaces conversacionais, interpretar uma mensagem corretamente não depende apenas das palavras presentes nela, mas também do contexto da interação.

### 3. Contraste e legibilidade da interface

**Problema**

Durante a utilização da interface local, alguns cartões de tarefas e lembretes apresentavam contraste insuficiente entre o texto e o fundo.

Embora as funcionalidades estivessem disponíveis, a leitura das informações ficava prejudicada.

**Correção**

Foram ajustados estilos visuais dos componentes para melhorar a legibilidade.

**Validação**

Após as alterações, os painéis foram inspecionados manualmente e os textos passaram a apresentar contraste adequado.

**Aprendizado**

A qualidade de uma aplicação não depende apenas da execução correta das operações. Clareza visual e usabilidade também fazem parte da experiência do usuário.

### 4. Limitações da interpretação baseada em regras

A avaliação determinística identificou casos em que o roteamento por regras não produziu o resultado esperado.

Dois exemplos documentados foram:

**EML-04 — Interpretação de solicitação de e-mail**

Uma solicitação envolvendo um e-mail de acompanhamento foi interpretada como criação de tarefa.

O caso demonstra uma limitação de regras baseadas em padrões de linguagem, especialmente quando diferentes intenções apresentam construções semelhantes.

**RAG-11 — Correspondência semântica na busca documental**

Uma pergunta sobre bolsa de estudos não recuperou adequadamente a informação correspondente a uma bolsa para cursos.

Esse comportamento evidencia uma limitação de buscas lexicais: palavras semanticamente relacionadas nem sempre possuem correspondência direta.

**Aprendizado**

Esses casos ajudam a identificar oportunidades de evolução, como melhorias nas regras, expansão de consultas ou utilização de recuperação semântica com embeddings.

Os dois casos permanecem documentados como limitações conhecidas na avaliação registrada, sem serem apresentados como problemas já resolvidos.

### 5. Publicação e diferenças entre ambientes

**Desafio**

Disponibilizar uma demonstração pública, gratuita e acessível sem exigir que visitantes instalassem Python ou configurassem credenciais de API.

**Solução adotada**

Foi utilizada uma versão estática da Lily Tasks, hospedada no Hugging Face Spaces, com interface em HTML, CSS e JavaScript.

Essa versão funciona diretamente no navegador e utiliza armazenamento local.

**Validação**

Foram testadas a criação e a consulta de tarefas, além da permanência dos dados após atualizar a página.

**Aprendizado**

A publicação permitiu compreender melhor a diferença entre a aplicação local, que possui backend e banco de dados, e uma demonstração estática, executada no navegador.

Também reforçou a importância de documentar claramente as capacidades e limitações de cada ambiente.

## 📈 Evolução do projeto

O desenvolvimento da Lily Tasks começou em ambiente local, com implementação de funcionalidades, experimentação, testes e correções antes da publicação do repositório no GitHub.

Por esse motivo, o histórico público de commits não representa integralmente todas as etapas iniciais de desenvolvimento.

A documentação técnica, os testes automatizados e os registros de avaliação complementam o histórico de versionamento, apresentando os principais desafios e decisões do projeto.

O processo de desenvolvimento envolveu:

1. Estruturação da aplicação e definição das funcionalidades.
2. Implementação da interface e dos serviços.
3. Integração dos componentes de interpretação e execução de ações.
4. Desenvolvimento da recuperação de informações em documentos.
5. Testes manuais para identificação de comportamentos inesperados.
6. Correções na interpretação de comandos e no tratamento de contexto.
7. Inclusão e execução de testes automatizados.
8. Ajustes de legibilidade e usabilidade.
9. Publicação do código no GitHub.
10. Disponibilização de uma demonstração pública no Hugging Face.

Essa evolução faz parte do objetivo educacional do projeto: desenvolver não apenas funcionalidades, mas também práticas de depuração, validação, documentação e manutenção.

## 💻 Como executar localmente

### Pré-requisitos

- Python compatível com as dependências do projeto.
- Git.
- Chave da API do Gemini, caso deseje utilizar o modo com LLM.

### 1. Clonar o repositório

```bash
git clone https://github.com/SimoesBia/lily-tasks.git
cd lily-tasks
```

### 2. Criar um ambiente virtual

No Windows:

```powershell
py -3.12 -m venv .venv
```

### 3. Ativar o ambiente virtual

**PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Prompt de Comando (CMD):**

```cmd
.venv\Scripts\activate
```

### 4. Instalar as dependências

```bash
python -m pip install -r requirements.txt
```

Para executar testes e utilizar as ferramentas de desenvolvimento, instale também as dependências de desenvolvimento:

```bash
python -m pip install -r requirements-dev.txt
```

### 5. Executar a aplicação

```bash
python app.py
```

A interface local estará disponível no endereço informado pelo terminal, normalmente:

http://127.0.0.1:7860

### 6. Configurar a integração com Gemini (opcional)

Crie um arquivo `.env` a partir do `.env.example` e configure sua chave:

```env
GEMINI_API_KEY=sua_chave_aqui
```

Sem a chave, a aplicação oferece um modo demonstração baseado em regras.

**Segurança:** nunca publique sua chave de API ou o arquivo `.env` no repositório.

## 🚀 Publicação no Hugging Face

A demonstração pública está disponível em:

**[Lily Tasks — Hugging Face Spaces](https://huggingface.co/spaces/SimoesBia/lily-tasks-demo)**

A publicação utiliza uma versão estática que funciona no navegador, sem backend Python, banco de dados remoto ou integração ativa com Gemini.

### Características da versão publicada

- Interface acessível pelo navegador.
- Comandos simulados por regras determinísticas.
- Gerenciamento básico de tarefas.
- Recursos demonstrativos de produtividade.
- Armazenamento de dados no `localStorage`.
- Ausência de necessidade de chave de API.

A versão estática pode ser encontrada no diretório [`static_space/`](static_space/).

Para mais informações sobre as opções de publicação, consulte [DEPLOYMENT.md](DEPLOYMENT.md).

## 🔒 Segurança e limitações

A Lily Tasks foi desenvolvida para fins educacionais e demonstrativos.

Algumas limitações importantes:

- A demonstração pública não executa um LLM.
- O armazenamento da versão estática é local ao navegador.
- A aplicação Python utiliza SQLite como banco de dados local.
- Os documentos utilizados para consultas são fictícios.
- Os rascunhos de e-mail não são enviados automaticamente.
- Os lembretes não oferecem notificações externas ou push.
- A busca BM25 depende da correspondência lexical entre a consulta e os documentos.
- Solicitações ambíguas podem exigir esclarecimentos adicionais.
- A integração com Gemini depende de credenciais, conectividade e disponibilidade do serviço.
- Ações sensíveis utilizam mecanismos de confirmação.
- Os resultados dos testes determinísticos não representam uma avaliação completa da qualidade do modelo de linguagem.

A aplicação inclui mecanismos de tratamento de erros e cuidados com conteúdo recuperado, mas não deve ser considerada uma solução de segurança validada para uso em produção.

## 📚 Documentação complementar

- [Arquitetura do sistema](ARCHITECTURE.md)
- [Avaliação e métricas](EVALUATION.md)
- [Segurança](SECURITY.md)
- [Publicação](DEPLOYMENT.md)
- [Tutorial de execução no Windows](docs/TUTORIAL_WINDOWS.md)

## 🎯 Aprendizados

O desenvolvimento da Lily Tasks proporcionou a aplicação prática de conceitos de inteligência artificial e engenharia de software.

Entre os principais aprendizados estão:

- Estruturação de aplicações Python em módulos.
- Integração entre interface, API e serviços internos.
- Utilização de modelos de linguagem e ferramentas.
- Recuperação de informações com BM25 e conceitos de RAG.
- Manipulação e persistência de dados com SQLite.
- Tratamento de ambiguidades em comandos conversacionais.
- Identificação e reprodução de bugs.
- Desenvolvimento de testes automatizados.
- Prevenção de regressões.
- Interpretação de resultados de avaliação.
- Documentação de limitações e decisões técnicas.
- Publicação e versionamento de projetos.
- Diferenças entre ambientes locais e demonstrações hospedadas.

Mais do que implementar uma aplicação funcional, o projeto foi uma oportunidade de compreender a importância de testar hipóteses, investigar comportamentos inesperados e melhorar o software a partir dos resultados observados.

## 🔮 Próximos passos

Entre as possibilidades de evolução do projeto estão:

- Ampliar a cobertura de testes com cenários independentes.
- Melhorar o tratamento de comandos ambíguos.
- Avaliar a integração real com Gemini em diferentes tipos de solicitação.
- Explorar recuperação semântica com embeddings.
- Aprimorar a experiência de uso e a acessibilidade.
- Evoluir a documentação e o processo de avaliação.

## 📄 Licença

Este projeto está disponível sob a [Licença MIT](LICENSE).

---

**Desenvolvido como projeto de estudo e portfólio em Engenharia de Software e Inteligência Artificial.**