# pdf-ingest-langchain

Sistema CLI em Python que ingere um PDF e responde perguntas sobre seu conteúdo via terminal, usando embeddings OpenAI e busca vetorial com PostgreSQL + pgVector.

---

## Pré-requisitos

- Python 3.11+
- Docker e Docker Compose
- Conta OpenAI com chave de API

---

## Instalação

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd pdf-ingest-langchain

# 2. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 3. Instale as dependências
pip install -r requirements.txt
```

---

## Configuração

```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais e configurações:

```env
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/vectordb
PG_VECTOR_COLLECTION_NAME=pdf_documents
PDF_PATH=document.pdf
```

| Variável | Descrição |
|---|---|
| `OPENAI_API_KEY` | Chave de API da OpenAI |
| `OPENAI_EMBEDDING_MODEL` | Modelo de embeddings a utilizar |
| `DATABASE_URL` | Connection string do PostgreSQL |
| `PG_VECTOR_COLLECTION_NAME` | Nome da collection no pgVector |
| `PDF_PATH` | Caminho do PDF a ser ingerido |

> O `.env` está no `.gitignore` e nunca será commitado.

---

## Subindo o banco de dados

```bash
docker compose up -d
```

Isso sobe um container PostgreSQL 15 com a extensão pgVector habilitada na porta `5432`.

Para verificar se está rodando:

```bash
docker compose ps
```

---

## Ingestão do PDF

Coloque o arquivo `document.pdf` na raiz do projeto e execute:

```bash
python src/ingest.py
```

Saída esperada:

```
Carregando PDF: document.pdf
Páginas carregadas: 12
Chunks gerados: 47
Gravando vetores no banco...
Ingestão concluída com sucesso.
```

> A ingestão só precisa ser feita uma vez por documento. Execute novamente se trocar o PDF.

---

## Chat

```bash
python src/chat.py
```

Saída esperada:

```
Sistema de perguntas sobre PDF. Digite 'exit' ou 'quit' para sair.

PERGUNTA: Qual é o tema principal do documento?
RESPOSTA: O documento trata de ...

PERGUNTA: exit
Encerrando. Até logo!
```

O sistema responde **somente com base no conteúdo do PDF**. Para perguntas fora do escopo:

```
PERGUNTA: Qual é a capital da França?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

---

## Testes

```bash
pytest
```

Os testes são unitários e não requerem banco ou chave de API — todas as dependências externas são mockadas.

Saída esperada:

```
26 passed in 0.89s
```

---

## Estrutura do projeto

```
pdf-ingest-langchain/
├── docker-compose.yml        # PostgreSQL + pgVector
├── requirements.txt
├── .env.example
├── conftest.py               # configuração do pytest
├── document.pdf              # PDF a ser ingerido (não versionado)
├── docs/                     # Especificações do projeto
├── src/
│   ├── ingest.py             # Ingestão do PDF
│   ├── search.py             # Busca e resposta via LLM
│   └── chat.py               # Entrypoint CLI
└── tests/
    ├── test_ingest.py
    ├── test_search.py
    └── test_chat.py
```

---

## Modelos utilizados

| Função     | Modelo                  |
|------------|-------------------------|
| Embeddings | `text-embedding-3-small` |
| LLM        | `gpt-5-nano`            |

---

## Encerrando o banco

```bash
docker compose down
```

Para remover também os dados persistidos:

```bash
docker compose down -v
```
