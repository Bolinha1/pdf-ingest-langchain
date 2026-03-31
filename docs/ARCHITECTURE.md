# ARCHITECTURE.md — pdf-ingest-langchain

> Versão: 1.0  
> Status: Draft  
> Método: Specification-Driven Development (SDD)

---

## 1. Visão Geral

O sistema é organizado em **3 camadas horizontais** com dependência unidirecional — cada camada conhece apenas a camada imediatamente abaixo dela.

**Princípio central:** nenhuma camada conhece a camada acima dela. O acoplamento flui em uma única direção: `chat.py → services → config → infra`.

---

## 1.1 Desenho Arquitetural

![Diagrama de arquitetura](./architecture-diagram.svg)

---

## 2. Responsabilidade de Cada Camada

### 2.1 `config/settings.py` — Camada de Configuração

**Responsabilidade única:** instanciar e expor as conexões externas.

O que faz:
- Lê variáveis de ambiente (`.env`)
- Instancia o cliente de embeddings (`OpenAIEmbeddings`)
- Instancia o cliente LLM (`ChatOpenAI`)
- Instancia a conexão com o banco vetorial (`PGVector`)

O que **não** faz:
- Nenhuma lógica de negócio
- Nenhuma interação com o usuário
- Nenhum conhecimento sobre PDF ou perguntas

---

### 2.2 `services/ingest_service.py` — Serviço de Ingestão

**Responsabilidade única:** ler o PDF e persistir os vetores no banco.

Fluxo interno:
```
load_pdf(path)
    └─> split_documents(docs)
            └─> store_embeddings(chunks)
```

Funções previstas:
- `load_pdf(path: str) -> list[Document]`
- `split_documents(docs: list[Document]) -> list[Document]`
- `store_embeddings(chunks: list[Document]) -> None`
- `run_ingestion(pdf_path: str) -> None`  ← orquestra as 3 acima

Depende de: `config/settings.py`  
Não conhece: `chat.py`, `search_service.py`

---

### 2.3 `services/search_service.py` — Serviço de Busca

**Responsabilidade única:** buscar chunks relevantes e gerar a resposta via LLM.

Fluxo interno:
```
search_chunks(query)
    └─> build_prompt(query, chunks)
            └─> ask_llm(prompt)
                    └─> str (resposta final)
```

Funções previstas:
- `search_chunks(query: str) -> list[tuple[Document, float]]`
- `build_prompt(query: str, chunks: list) -> str`
- `ask_llm(prompt: str) -> str`
- `answer_question(query: str) -> str`  ← orquestra as 3 acima

Depende de: `config/settings.py`  
Não conhece: `chat.py`, `ingest_service.py`

---

### 2.4 `chat.py` — Entrypoint CLI

**Responsabilidade única:** interagir com o usuário em loop via terminal.

Fluxo:
```
while True:
    pergunta = input("PERGUNTA: ")
    resposta = answer_question(pergunta)
    print(f"RESPOSTA: {resposta}")
```

O que faz:
- Recebe input do usuário
- Chama `answer_question()` do `search_service`
- Exibe a resposta formatada
- Trata saída do loop (ex: `exit`, `quit`, Ctrl+C)

Depende de: `services/search_service.py`  
Não conhece: `config/settings.py` diretamente

---

## 3. Fluxo de Dados — Ingestão (UC-1)

```
[document.pdf]
      │
      ▼
ingest_service.load_pdf()
      │  list[Document]
      ▼
ingest_service.split_documents()
      │  list[Document] (chunks de 1000 chars, overlap 150)
      ▼
ingest_service.store_embeddings()
      │  chama settings.embeddings + settings.vector_store
      ▼
[PostgreSQL + pgVector]
```

---

## 4. Fluxo de Dados — Busca e Resposta (UC-2/3/4)

```
[Usuário digita pergunta]
      │  str
      ▼
chat.py → search_service.answer_question(query)
                │
                ├─> search_chunks(query)
                │       │  usa settings.vector_store
                │       │  similarity_search_with_score(k=10)
                │       └─> list[tuple[Document, float]]
                │
                ├─> build_prompt(query, chunks)
                │       └─> str (prompt com contexto + regras)
                │
                └─> ask_llm(prompt)
                        │  usa settings.llm
                        └─> str (resposta)
      │
      ▼
[Usuário vê a resposta]
```

---

## 5. Diagrama de Dependências

```
chat.py
  └── services/search_service.py
        └── config/settings.py
              ├── OpenAIEmbeddings  (OpenAI API)
              ├── ChatOpenAI        (OpenAI API)
              └── PGVector                      (PostgreSQL)

src/services/ingest_service.py   ← executado separadamente
  └── config/settings.py
        ├── OpenAIEmbeddings
        └── PGVector
```

Regra: **nenhuma seta aponta para cima** neste diagrama.

---

## 6. Variáveis de Ambiente

| Variável | Usada em | Descrição |
|---|---|---|
| `OPENAI_API_KEY` | `settings.py` | Chave da API OpenAI |
| `DATABASE_URL` | `settings.py` | Connection string PostgreSQL |

Formato esperado no `.env`:
```
OPENAI_API_KEY=sua_chave_aqui
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/vectordb
```

---

## 7. Infraestrutura (Docker)

O `docker-compose.yml` sobe um container PostgreSQL com a extensão `pgvector` habilitada. O banco é o único serviço externo gerenciado localmente — a OpenAI API é consumida diretamente via HTTP.

```
docker compose up -d
    └─> postgres:15 + pgvector
            └─> porta 5432 exposta para o host
```

---

## 8. Estratégia de Testes (TDD)

Cada módulo possui um arquivo de teste correspondente em `tests/`, seguindo o padrão Python. Os testes são escritos **antes** da implementação — o código de produção só é escrito para fazer um teste falho passar.

| Módulo | Arquivo de teste |
|---|---|
| `config/settings.py` | `tests/test_settings.py` |
| `services/ingest_service.py` | `tests/test_ingest_service.py` |
| `services/search_service.py` | `tests/test_search_service.py` |
| `chat.py` | `tests/test_chat.py` |

Regras:

- Dependências externas (LLM, banco, embeddings) são mockadas nos testes unitários
- A suite completa deve passar com `pytest` a partir da raiz do projeto
- Nenhuma função de produção é adicionada sem um teste correspondente

---

## 9. Decisões de Design

| Decisão | Justificativa |
|---|---|
| `settings.py` centralizado | Evita instanciar clientes em múltiplos lugares; facilita troca de provedor |
| Serviços sem estado | Funções puras facilitam testes e reuso |
| `chat.py` sem lógica de negócio | Separação clara entre I/O e processamento |
| `ingest_service` executado separadamente | Ingestão é uma operação de setup, não de runtime |
| Prompt como string em `search_service` | Mantém o contrato do prompt versionável e testável |

---

## 10. Próximos Passos (SDD)

```
[x] docs/SPEC.md         ← concluído
[x] docs/ARCHITECTURE.md ← concluído
[ ] docs/CONTRACTS.md    ← assinaturas de funções e schemas de dados
[ ] Implementação        ← src/config/settings.py, src/services/*, src/chat.py
[ ] README.md            ← instruções finais de execução
```
