import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import vector_store


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
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "document.pdf"
    run_ingestion(pdf_path)
