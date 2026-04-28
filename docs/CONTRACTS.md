# CONTRACTS.md — pdf-ingest-langchain

> Versão: 1.0  
> Status: Draft  
> Método: Specification-Driven Development (SDD)

Este documento define os **contratos de cada função** do sistema — assinaturas, tipos, pré-condições, pós-condições e regras de comportamento. O Claude Code deve seguir estes contratos à risca durante a implementação.

---

## 1. `src/ingest.py` e `src/search.py` — Configuração inline

Cada script inicializa e expõe **instâncias** prontas no topo do módulo.

### Objetos exportados

| Nome | Tipo | Descrição |
|---|---|---|
| `embeddings` | `OpenAIEmbeddings` | Cliente de embeddings OpenAI |
| `llm` | `ChatOpenAI` | Cliente LLM OpenAI |
| `vector_store` | `PGVector` | Conexão com o banco vetorial |

### Configurações obrigatórias

```python
# Embeddings
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY")
)

# LLM
llm = ChatOpenAI(
    model="gpt-5-nano",
    api_key=os.getenv("OPENAI_API_KEY")
)

# Vector Store
vector_store = PGVector(
    embeddings=embeddings,
    collection_name="pdf_documents",
    connection=os.getenv("DATABASE_URL")
)
```

### Regras

- Deve usar `python-dotenv` para carregar o `.env` automaticamente
- Se `OPENAI_API_KEY` ou `DATABASE_URL` estiverem ausentes, deve lançar erro claro na inicialização
- Nenhuma lógica condicional ou de negócio neste arquivo

---

## 2. `src/ingest.py`

### 2.1 `load_pdf`

```python
def load_pdf(path: str) -> list[Document]:
```

| | Descrição |
|---|---|
| **Entrada** | `path` — caminho absoluto ou relativo para o arquivo `.pdf` |
| **Saída** | Lista de objetos `Document` (um por página do PDF) |
| **Pré-condição** | O arquivo existe e é um PDF válido |
| **Pós-condição** | Retorna lista não-vazia de documentos |
| **Erro esperado** | `FileNotFoundError` se o arquivo não existir |
| **Implementação** | Usar `PyPDFLoader(path).load()` |

---

### 2.2 `split_documents`

```python
def split_documents(docs: list[Document]) -> list[Document]:
```

| | Descrição |
|---|---|
| **Entrada** | Lista de `Document` retornada por `load_pdf` |
| **Saída** | Lista de `Document` fragmentados em chunks |
| **Pré-condição** | `docs` não pode ser lista vazia |
| **Pós-condição** | Cada chunk tem no máximo 1000 caracteres |
| **Implementação** | Usar `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)` |

---

### 2.3 `store_embeddings`

```python
def store_embeddings(chunks: list[Document]) -> None:
```

| | Descrição |
|---|---|
| **Entrada** | Lista de chunks retornada por `split_documents` |
| **Saída** | `None` — efeito colateral: vetores gravados no banco |
| **Pré-condição** | Banco PostgreSQL acessível via `DATABASE_URL` |
| **Pós-condição** | Todos os chunks estão persistidos no pgVector |
| **Implementação** | Usar `PGVector.from_documents(chunks, embeddings, ...)` ou `vector_store.add_documents(chunks)` |
| **Erro esperado** | `Exception` com mensagem clara se o banco estiver inacessível |

---

### 2.4 `run_ingestion` ← função orquestradora

```python
def run_ingestion(pdf_path: str) -> None:
```

| | Descrição |
|---|---|
| **Entrada** | `pdf_path` — caminho para o arquivo PDF |
| **Saída** | `None` |
| **Responsabilidade** | Orquestra `load_pdf → split_documents → store_embeddings` |
| **Saída no terminal** | Deve imprimir progresso: total de páginas, total de chunks, confirmação de gravação |
| **Ponto de entrada** | Chamada no bloco `if __name__ == "__main__"` |

Exemplo de saída esperada no terminal:
```
Carregando PDF: document.pdf
Páginas carregadas: 12
Chunks gerados: 47
Gravando vetores no banco...
Ingestão concluída com sucesso.
```

---

## 3. `src/search.py`

### 3.1 `search_chunks`

```python
def search_chunks(query: str) -> list[tuple[Document, float]]:
```

| | Descrição |
|---|---|
| **Entrada** | `query` — pergunta do usuário em linguagem natural |
| **Saída** | Lista de tuplas `(Document, score)` ordenadas por relevância |
| **Pré-condição** | `query` não pode ser string vazia |
| **Pós-condição** | Retorna exatamente `k=10` resultados (ou menos se o banco tiver menos) |
| **Implementação** | Usar `vector_store.similarity_search_with_score(query, k=10)` |

---

### 3.2 `build_prompt`

```python
def build_prompt(query: str, chunks: list[tuple[Document, float]]) -> str:
```

| | Descrição |
|---|---|
| **Entrada** | `query` — pergunta do usuário; `chunks` — resultado de `search_chunks` |
| **Saída** | String com o prompt completo pronto para envio à LLM |
| **Pré-condição** | `chunks` não pode ser lista vazia |
| **Pós-condição** | O prompt retornado deve seguir o template definido no SPEC.md seção 5 — sem alterações |
| **Regra** | O contexto é montado concatenando `doc.page_content` de cada chunk, separados por `\n---\n` |

Template obrigatório:
```
CONTEXTO:
{conteúdo dos chunks concatenados}

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
{query}

RESPONDA A "PERGUNTA DO USUÁRIO"
```

---

### 3.3 `ask_llm`

```python
def ask_llm(prompt: str) -> str:
```

| | Descrição |
|---|---|
| **Entrada** | `prompt` — string completa retornada por `build_prompt` |
| **Saída** | Resposta da LLM como string pura |
| **Pré-condição** | `OPENAI_API_KEY` válida e configurada |
| **Pós-condição** | Retorna string não-vazia |
| **Implementação** | Usar `llm.invoke(prompt)` e extrair `.content` da resposta |

---

### 3.4 `answer_question` ← função orquestradora

```python
def answer_question(query: str) -> str:
```

| | Descrição |
|---|---|
| **Entrada** | `query` — pergunta do usuário |
| **Saída** | Resposta final como string |
| **Responsabilidade** | Orquestra `search_chunks → build_prompt → ask_llm` |
| **Pré-condição** | `query` não pode ser string vazia ou apenas espaços |
| **Pós-condição** | Sempre retorna uma string — nunca lança exceção para o chamador |
| **Regra de erro** | Em caso de falha interna, retorna mensagem amigável ao invés de propagar exceção |

---

## 4. `chat.py`

`chat.py` não define funções reutilizáveis — é um script de entrypoint. Seus contratos são comportamentais.

### Comportamentos obrigatórios

| Comportamento | Descrição |
|---|---|
| Loop contínuo | Mantém o terminal ativo até o usuário sair |
| Prompt de entrada | Exibe exatamente `PERGUNTA: ` antes de cada input |
| Exibição da resposta | Exibe exatamente `RESPOSTA: ` seguido da resposta da LLM |
| Saída limpa | Aceita `exit`, `quit` ou `Ctrl+C` para encerrar sem erro |
| Linha em branco | Ignora silenciosamente inputs vazios (sem chamar a LLM) |

### Formato de saída esperado

```
PERGUNTA: Qual o faturamento da empresa?
RESPOSTA: O faturamento foi de 10 milhões de reais.

PERGUNTA: Qual a capital da França?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.

PERGUNTA: exit
Encerrando. Até logo!
```

---

## 5. Tipos e Imports Esperados

```python
# Tipos LangChain utilizados no projeto
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector

# Utilitários
import os
from dotenv import load_dotenv
```

---

## 6. Variáveis de Ambiente Esperadas

| Variável | Exemplo | Obrigatória |
|---|---|---|
| `OPENAI_API_KEY` | `sk-...` | Sim |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@localhost:5432/vectordb` | Sim |

---

## 7. Contratos de Teste (TDD)

Cada módulo possui um arquivo de teste correspondente. Dependências externas (LLM, embeddings, banco) devem ser mockadas — os testes são unitários e não requerem serviços rodando.

### `tests/test_ingest.py`

- Dado que `OPENAI_API_KEY` e `DATABASE_URL` estão definidas, `embeddings` e `vector_store` são instanciados sem erro
- Dado que `OPENAI_API_KEY` está ausente, a inicialização lança exceção com mensagem clara
- Dado que `DATABASE_URL` está ausente, a inicialização lança exceção com mensagem clara

- `load_pdf` retorna lista não-vazia de `Document` para um PDF válido
- `load_pdf` lança `FileNotFoundError` para caminho inexistente
- `split_documents` retorna chunks com no máximo 1000 caracteres
- `split_documents` lança erro para lista vazia de documentos
- `store_embeddings` chama `vector_store.add_documents` com os chunks (mock)
- `run_ingestion` orquestra as três funções na ordem correta

### `tests/test_search.py`

- `search_chunks` chama `vector_store.similarity_search_with_score` com `k=10` (mock)
- `search_chunks` lança erro para query vazia
- `build_prompt` retorna string contendo o contexto e a query no template correto
- `build_prompt` lança erro para lista de chunks vazia
- `ask_llm` chama `llm.invoke` e retorna `.content` da resposta (mock)
- `answer_question` retorna mensagem amigável em caso de falha interna (sem propagar exceção)

### `tests/test_chat.py`

- Input vazio não chama `answer_question`
- Input `exit` encerra o loop sem erro
- Input válido exibe `RESPOSTA:` seguido da resposta de `answer_question` (mock)

---

## 8. Próximos Passos (SDD)

```
[x] docs/SPEC.md         ← concluído
[x] docs/ARCHITECTURE.md ← concluído
[x] docs/CONTRACTS.md    ← concluído
[x] Testes (TDD)         ← tests/test_ingest.py, tests/test_search.py, tests/test_chat.py
[x] Implementação        ← src/ingest.py, src/search.py, src/chat.py
[ ] README.md            ← instruções finais de execução
```
