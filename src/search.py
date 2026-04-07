import os

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector
from langchain_core.documents import Document

load_dotenv()

_api_key = os.getenv("OPENAI_API_KEY")
_db_url = os.getenv("DATABASE_URL")

if not _api_key:
    raise EnvironmentError("OPENAI_API_KEY não definida no ambiente.")
if not _db_url:
    raise EnvironmentError("DATABASE_URL não definida no ambiente.")

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=_api_key,
)

llm = ChatOpenAI(
    model="gpt-5-nano",
    api_key=_api_key,
)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name="pdf_documents",
    connection=_db_url,
)


def search_chunks(query: str) -> list[tuple[Document, float]]:
    if not query or not query.strip():
        raise ValueError("A query não pode ser vazia.")
    return vector_store.similarity_search_with_score(query, k=10)


def build_prompt(query: str, chunks: list[tuple[Document, float]]) -> str:
    if not chunks:
        raise ValueError("A lista de chunks não pode ser vazia.")
    context = "\n---\n".join(doc.page_content for doc, _ in chunks)
    return (
        f"CONTEXTO:\n{context}\n\n"
        "REGRAS:\n"
        "- Responda somente com base no CONTEXTO.\n"
        "- Se a informação não estiver explicitamente no CONTEXTO, responda:\n"
        '  "Não tenho informações necessárias para responder sua pergunta."\n'
        "- Nunca invente ou use conhecimento externo.\n"
        "- Nunca produza opiniões ou interpretações além do que está escrito.\n\n"
        "EXEMPLOS DE PERGUNTAS FORA DO CONTEXTO:\n"
        'Pergunta: "Qual é a capital da França?"\n'
        'Resposta: "Não tenho informações necessárias para responder sua pergunta."\n\n'
        'Pergunta: "Quantos clientes temos em 2024?"\n'
        'Resposta: "Não tenho informações necessárias para responder sua pergunta."\n\n'
        'Pergunta: "Você acha isso bom ou ruim?"\n'
        'Resposta: "Não tenho informações necessárias para responder sua pergunta."\n\n'
        f"PERGUNTA DO USUÁRIO:\n{query}\n\n"
        'RESPONDA A "PERGUNTA DO USUÁRIO"'
    )


def ask_llm(prompt: str) -> str:
    response = llm.invoke(prompt)
    return response.content


def answer_question(query: str) -> str:
    try:
        chunks = search_chunks(query)
        prompt = build_prompt(query, chunks)
        return ask_llm(prompt)
    except Exception:
        return "Ocorreu um erro ao processar sua pergunta. Tente novamente."
