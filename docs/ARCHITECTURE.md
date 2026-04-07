# ARCHITECTURE.md — pdf-ingest-langchain

> Versão: 1.0  
> Status: Draft  
> Método: Specification-Driven Development (SDD)

---

## 1. Visão Geral

O sistema é organizado em **3 scripts planos** em `src/` com dependência unidirecional.

**Princípio central:** o acoplamento flui em uma única direção: `chat.py → search.py → [infra]`.

---

## 1.1 Desenho Arquitetural

![Diagrama de arquitetura](./architecture-diagram.svg)

---

## 2. Responsabilidade de Cada Script

### 2.1 `src/ingest.py` — Ingestão do PDF

**Responsabilidade única:** ler o PDF e persistir os vetores no banco.

Inicializa no topo do módulo:
- Valida variáveis de ambiente (`OPENAI_API_KEY`, `DATABASE_URL`)
- Instancia `embeddings` (`OpenAIEmbeddings`) e `vector_store` (`PGVector`)

Fluxo interno:
```
load_pdf(path)
    └─> split_documents(docs)
            └─> store_embeddings(chunks)
```

Funções:
- `load_pdf(path: str) -> list[Document]`
- `split_documents(docs: list[Document]) -> list[Document]`
- `store_embeddings(chunks: list[Document]) -> None`
- `run_ingestion(pdf_path: str) -> None`  ← orquestra as 3 acima

Executado separadamente via `python src/ingest.py`. Não conhece `chat.py` ou `search.py`.

---

### 2.2 `src/search.py` — Busca e Resposta via LLM

**Responsabilidade única:** buscar chunks relevantes e gerar a resposta via LLM.

Inicializa no topo do módulo:
- Valida variáveis de ambiente
- Instancia `embeddings`, `llm` (`ChatOpenAI`) e `vector_store`

Fluxo interno:
```
search_chunks(query)
    └─> build_prompt(query, chunks)
            └─> ask_llm(prompt)
                    └─> str (resposta final)
```

Funções:
- `search_chunks(query: str) -> list[tuple[Document, float]]`
- `build_prompt(query: str, chunks: list) -> str`
- `ask_llm(prompt: str) -> str`
- `answer_question(query: str) -> str`  ← orquestra as 3 acima

Não conhece `chat.py` ou `ingest.py`.

---

### 2.3 `src/chat.py` — Entrypoint CLI

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
- Chama `answer_question()` de `search`
- Exibe a resposta formatada
- Trata saída do loop (ex: `exit`, `quit`, Ctrl+C)

Depende de: `search.py`  
Não conhece: detalhes de embeddings, banco ou LLM diretamente

---

## 3. Fluxo de Dados — Ingestão (UC-1)

```
[document.pdf]
      │
      ▼
ingest.load_pdf()
      │  list[Document]
      ▼
ingest.split_documents()
      │  list[Document] (chunks de 1000 chars, overlap 150)
      ▼
ingest.store_embeddings()
      │  usa ingest.embeddings + ingest.vector_store
      ▼
[PostgreSQL + pgVector]
```

---

## 4. Fluxo de Dados — Busca e Resposta (UC-2/3/4)

```
[Usuário digita pergunta]
      │  str
      ▼
chat.py → search.answer_question(query)
                │
                ├─> search_chunks(query)
                │       │  usa search.vector_store
                │       │  similarity_search_with_score(k=10)
                │       └─> list[tuple[Document, float]]
                │
                ├─> build_prompt(query, chunks)
                │       └─> str (prompt com contexto + regras)
                │
                └─> ask_llm(prompt)
                        │  usa search.llm
                        └─> str (resposta)
      │
      ▼
[Usuário vê a resposta]
```

---

## 5. Diagrama de Dependências

```
chat.py
  └── search.py
        ├── OpenAIEmbeddings  (OpenAI API)
        ├── ChatOpenAI        (OpenAI API)
        └── PGVector          (PostgreSQL)

ingest.py   ← executado separadamente
  ├── OpenAIEmbeddings
  └── PGVector
```

Regra: **nenhuma seta aponta para cima** neste diagrama.

---

## 6. Variáveis de Ambiente

| Variável | Usada em | Descricao |
|---|---|---|
| `OPENAI_API_KEY` | `ingest.py`, `search.py` | Chave da API OpenAI |
| `DATABASE_URL` | `ingest.py`, `search.py` | Connection string PostgreSQL |

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
| `src/ingest.py` | `tests/test_ingest.py` |
| `src/search.py` | `tests/test_search.py` |
| `src/chat.py` | `tests/test_chat.py` |

Regras:

- Dependências externas (LLM, banco, embeddings) são mockadas nos testes unitários
- A suite completa deve passar com `pytest` a partir da raiz do projeto
- Nenhuma função de produção é adicionada sem um teste correspondente

---

## 9. Decisões de Design

| Decisão | Justificativa |
|---|---|
| Scripts planos em `src/` | Estrutura simples sem subpacotes; fácil de executar e entender |
| Config inline em `ingest.py` e `search.py` | Cada script é autossuficiente; sem acoplamento via módulo compartilhado |
| Funções sem estado | Funções puras facilitam testes e reuso |
| `chat.py` sem lógica de negócio | Separação clara entre I/O e processamento |
| `ingest.py` executado separadamente | Ingestão é uma operação de setup, não de runtime |
| Prompt como string em `search.py` | Mantém o contrato do prompt versionável e testável |

---

## 10. Próximos Passos (SDD)

```
[x] docs/SPEC.md         ← concluído
[x] docs/ARCHITECTURE.md ← concluído
[ ] docs/CONTRACTS.md    ← assinaturas de funções e schemas de dados
[ ] Implementação        ← src/config/settings.py, src/services/*, src/chat.py
[ ] README.md            ← instruções finais de execução
```
