import os
import sys

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

_api_key = os.getenv("OPENAI_API_KEY")
_db_url = os.getenv("DATABASE_URL")
_embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL")
_collection_name = os.getenv("PG_VECTOR_COLLECTION_NAME")
_pdf_path = os.getenv("PDF_PATH")

if not _api_key:
    raise EnvironmentError("OPENAI_API_KEY não definida no ambiente.")
if not _db_url:
    raise EnvironmentError("DATABASE_URL não definida no ambiente.")
if not _embedding_model:
    raise EnvironmentError("OPENAI_EMBEDDING_MODEL não definida no ambiente.")
if not _collection_name:
    raise EnvironmentError("PG_VECTOR_COLLECTION_NAME não definida no ambiente.")
if not _pdf_path:
    raise EnvironmentError("PDF_PATH não definida no ambiente.")

embeddings = OpenAIEmbeddings(
    model=_embedding_model,
    api_key=_api_key,
)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name=_collection_name,
    connection=_db_url,
)


def load_pdf(path: str) -> list[Document]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    loader = PyPDFLoader(path)
    return loader.load()


def split_documents(docs: list[Document]) -> list[Document]:
    if not docs:
        raise ValueError("A lista de documentos não pode ser vazia.")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    return splitter.split_documents(docs)


def store_embeddings(chunks: list[Document]) -> None:
    try:
        vector_store.add_documents(chunks)
    except Exception as e:
        raise Exception(f"Erro ao gravar vetores no banco: {e}") from e


def run_ingestion(pdf_path: str) -> None:
    print(f"Carregando PDF: {pdf_path}")
    docs = load_pdf(pdf_path)
    print(f"Páginas carregadas: {len(docs)}")
    chunks = split_documents(docs)
    print(f"Chunks gerados: {len(chunks)}")
    print("Gravando vetores no banco...")
    store_embeddings(chunks)
    print("Ingestão concluída com sucesso.")


if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else _pdf_path
    run_ingestion(pdf_path)
