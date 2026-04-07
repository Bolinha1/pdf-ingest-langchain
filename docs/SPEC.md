# SPEC.md — pdf-ingest-langchain

> Versão: 1.0  
> Status: Draft  
> Método: Specification-Driven Development (SDD)

---

## 1. Visão Geral

Sistema CLI em Python capaz de:

1. **Ingerir** um arquivo PDF, dividindo-o em chunks, convertendo em embeddings e persistindo em PostgreSQL + pgVector.
2. **Responder perguntas** via terminal com base exclusivamente no conteúdo do PDF ingerido.

---

## 2. Atores e Casos de Uso

### Ator: Usuário (desenvolvedor via CLI)

| ID   | Caso de Uso              | Descrição                                                                 |
|------|--------------------------|---------------------------------------------------------------------------|
| UC-1 | Ingerir PDF              | Usuário executa `python src/ingest.py` e o PDF é processado e armazenado |
| UC-2 | Fazer pergunta           | Usuário executa `python src/chat.py` e digita perguntas em loop                            |
| UC-3 | Receber resposta         | Sistema retorna resposta baseada apenas no conteúdo do PDF                |
| UC-4 | Pergunta fora do escopo  | Sistema responde com mensagem padrão de "sem informação"                  |

---

## 3. Comportamentos Esperados

### UC-1 — Ingestão

- **Entrada:** arquivo `document.pdf` na raiz do projeto
- **Processamento:**
  - Leitura do PDF via `PyPDFLoader`
  - Divisão em chunks de **1000 caracteres** com **overlap de 150**
  - Geração de embeddings via `OpenAIEmbeddings` (modelo: `text-embedding-3-small`)
  - Persistência no PostgreSQL via `PGVector`
- **Saída esperada:** mensagem de confirmação no terminal; vetores gravados no banco
- **Pré-condição:** banco PostgreSQL rodando via Docker Compose
- **Pós-condição:** coleção de vetores disponível para busca

### UC-2 / UC-3 — Busca e Resposta

- **Entrada:** pergunta digitada pelo usuário no terminal
- **Processamento:**
  1. Vetorizar a pergunta com o mesmo modelo de embeddings
  2. Buscar os **10 chunks mais relevantes** (`k=10`) via `similarity_search_with_score`
  3. Montar prompt com o contexto recuperado (ver Seção 5)
  4. Chamar LLM (`gpt-5-nano`) com o prompt montado
  5. Exibir resposta no terminal
- **Saída esperada:** resposta em linguagem natural baseada no PDF

### UC-4 — Pergunta Fora do Contexto

- **Condição:** a pergunta não tem informação correspondente nos chunks recuperados
- **Saída obrigatória (literal):**
  ```
  Não tenho informações necessárias para responder sua pergunta.
  ```
- **Restrição:** o sistema **nunca** deve inventar, inferir ou usar conhecimento externo

---

## 4. Restrições Técnicas

| Categoria       | Decisão                                         |
|-----------------|-------------------------------------------------|
| Linguagem       | Python 3.11+                                    |
| Framework       | LangChain                                       |
| Embeddings      | `OpenAIEmbeddings` — `text-embedding-3-small`           |
| LLM             | `ChatOpenAI` — `gpt-5-nano`                             |
| Banco de dados  | PostgreSQL 15 + extensão pgVector               |
| Infraestrutura  | Docker + Docker Compose (fornecido)             |
| Chunk size      | 1000 caracteres                                 |
| Chunk overlap   | 150 caracteres                                  |
| Resultados k    | 10                                              |
| Variáveis env   | `OPENAI_API_KEY`, `DATABASE_URL`                |
| Testes          | pytest                                          |

---

## 5. Prompt Template (contrato imutável)

```
CONTEXTO:
{context}

REGRAS:
- Responda somente com base no CONTEXTO.
- Se a informação não estiver explicitamente no CONTEXTO, responda:
  "Não tenho informações necessárias para responder sua pergunta."
- Nunca invente ou use conhecimento externo.
- Nunca produza opiniões ou interpretações além do que está escrito.

EXEMPLOS DE PERGUNTAS FORA DO CONTEXTO:
Pergunta: "Qual é a capital da França?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Quantos clientes temos em 2024?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Você acha isso bom ou ruim?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

PERGUNTA DO USUÁRIO:
{question}

RESPONDA A "PERGUNTA DO USUÁRIO"
```

---

## 6. Estrutura de Arquivos

```
pdf-ingest-langchain/
├── docker-compose.yml        # Banco PostgreSQL + pgVector
├── requirements.txt          # Dependências Python
├── .env.example              # Template: OPENAI_API_KEY e DATABASE_URL
├── .env                      # (não versionar) variáveis reais
├── document.pdf              # PDF a ser ingerido
├── docs/                     # Documentação de especificação (commitada)
│   ├── SPEC.md               # Este documento
│   ├── ARCHITECTURE.md       # Arquitetura e fluxo entre módulos
│   └── CONTRACTS.md          # Assinaturas de funções e schemas
├── src/
│   ├── ingest.py             # UC-1: configuração + lê PDF, chunking, embeddings, persiste
│   ├── search.py             # UC-2/3: configuração + busca vetorial e montagem de resposta
│   └── chat.py               # Entrypoint CLI — orquestra search e exibe resposta
├── tests/                    # Testes automatizados (TDD)
│   ├── __init__.py
│   ├── test_ingest.py        # Testa env vars, load_pdf, split_documents, store_embeddings, run_ingestion
│   ├── test_search.py        # Testa search_chunks, build_prompt, ask_llm, answer_question
│   └── test_chat.py          # Testa comportamentos do entrypoint CLI
└── README.md                 # Instruções de execução
```

### Fluxo de dependências entre camadas

```
chat.py  →  services/  →  config/  →  [PostgreSQL | OpenAI API]
```

- `chat.py` conhece apenas `services/` — nunca `config/` diretamente
- `services/` conhece apenas `config/` — nunca detalhes do CLI
- `config/` conhece apenas dependências externas — não tem lógica de negócio
- O acoplamento flui em **uma única direção** (sem dependências circulares)

---

## 7. Critérios de Aceitação

| ID    | Critério                                                                 | Verificação                          |
|-------|--------------------------------------------------------------------------|--------------------------------------|
| AC-1  | `ingest.py` processa o PDF sem erros                                             | Execução sem exceção + log de chunks |
| AC-2  | Vetores são gravados no banco e consultáveis                              | Query direta no PostgreSQL           |
| AC-3  | `chat.py` responde perguntas dentro do escopo com base no PDF            | Teste manual com perguntas válidas   |
| AC-4  | Perguntas fora do escopo retornam a mensagem padrão (literal)            | Teste manual com perguntas inválidas |
| AC-5  | Nenhuma resposta usa conhecimento externo ao PDF                         | Revisão do prompt e testes           |
| AC-6  | Variáveis sensíveis ficam apenas no `.env` (não commitadas)              | `.gitignore` inclui `.env`           |
| AC-7  | Todos os testes unitários passam sem dependências externas reais         | `pytest` verde a partir da raiz      |

---

## 8. Fora do Escopo (v1.0)

- Interface web ou API REST
- Suporte a múltiplos PDFs simultâneos
- Autenticação de usuários
- Score mínimo de relevância configurável
- Logging estruturado em arquivo

---

## 9. Próximos Passos (SDD)

```
[x] docs/SPEC.md         ← concluído
[ ] docs/ARCHITECTURE.md ← como os módulos se conectam internamente
[ ] docs/CONTRACTS.md    ← assinaturas de funções e schemas de dados
[ ] Testes (TDD)         ← tests/test_settings.py, tests/test_ingest_service.py, tests/test_search_service.py, tests/test_chat.py
[ ] Implementação        ← src/config/settings.py, src/services/ingest_service.py, src/services/search_service.py, src/chat.py
[ ] README.md            ← instruções finais de execução
```