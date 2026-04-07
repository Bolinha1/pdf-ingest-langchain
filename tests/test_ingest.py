import importlib
import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from langchain_core.documents import Document

_VALID_ENV = {
    "OPENAI_API_KEY": "sk-test-key",
    "DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/testdb",
}


def _clear_ingest():
    if "ingest" in sys.modules:
        del sys.modules["ingest"]


@pytest.fixture(autouse=True)
def isolate_ingest_module():
    _clear_ingest()
    yield
    _clear_ingest()


# Import ingest once with valid env so function tests can use the module object
with (
    patch.dict(os.environ, _VALID_ENV, clear=True),
    patch("dotenv.load_dotenv"),
    patch("langchain_openai.OpenAIEmbeddings", return_value=MagicMock()),
    patch("langchain_postgres.PGVector", return_value=MagicMock()),
):
    import ingest as _ingest


ingest = _ingest


def _make_docs(n=3, content="texto de exemplo com mais de dez caracteres"):
    return [Document(page_content=content, metadata={"page": i}) for i in range(n)]


# --- Env validation tests (previously test_settings.py) ---


def test_instantiates_with_valid_env():
    with (
        patch.dict(os.environ, _VALID_ENV, clear=True),
        patch("dotenv.load_dotenv"),
        patch("langchain_openai.OpenAIEmbeddings", return_value=MagicMock()) as MockEmb,
        patch("langchain_postgres.PGVector", return_value=MagicMock()) as MockPG,
    ):
        mod = importlib.import_module("ingest")
        assert mod.embeddings is not None
        assert mod.vector_store is not None
        MockEmb.assert_called_once()
        MockPG.assert_called_once()


def test_raises_without_api_key():
    env = {"DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/testdb"}
    with (
        patch.dict(os.environ, env, clear=True),
        patch("dotenv.load_dotenv"),
        patch("langchain_openai.OpenAIEmbeddings"),
        patch("langchain_postgres.PGVector"),
    ):
        with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
            importlib.import_module("ingest")


def test_raises_without_database_url():
    env = {"OPENAI_API_KEY": "sk-test-key"}
    with (
        patch.dict(os.environ, env, clear=True),
        patch("dotenv.load_dotenv"),
        patch("langchain_openai.OpenAIEmbeddings"),
        patch("langchain_postgres.PGVector"),
    ):
        with pytest.raises(EnvironmentError, match="DATABASE_URL"):
            importlib.import_module("ingest")


# --- Ingest function tests ---


@pytest.fixture
def mock_vector_store():
    with patch.object(ingest, "vector_store") as m:
        yield m


class TestLoadPdf:
    def test_returns_documents_for_valid_pdf(self, tmp_path):
        pdf_file = tmp_path / "file.pdf"
        pdf_file.touch()
        fake_docs = _make_docs()
        with patch.object(ingest, "PyPDFLoader") as MockLoader:
            MockLoader.return_value.load.return_value = fake_docs
            result = ingest.load_pdf(str(pdf_file))

        assert result == fake_docs

    def test_raises_file_not_found_for_missing_path(self):
        with pytest.raises(FileNotFoundError):
            ingest.load_pdf("/caminho/inexistente/arquivo.pdf")


class TestSplitDocuments:
    def test_returns_chunks_for_valid_docs(self):
        long_text = "palavra " * 300  # ~2400 chars → deve gerar vários chunks
        docs = [Document(page_content=long_text)]
        chunks = ingest.split_documents(docs)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.page_content) <= 1000

    def test_raises_for_empty_list(self):
        with pytest.raises(ValueError):
            ingest.split_documents([])


class TestStoreEmbeddings:
    def test_calls_add_documents_with_chunks(self, mock_vector_store):
        chunks = _make_docs()
        ingest.store_embeddings(chunks)
        mock_vector_store.add_documents.assert_called_once_with(chunks)

    def test_raises_on_db_error(self, mock_vector_store):
        mock_vector_store.add_documents.side_effect = Exception("conexão recusada")
        with pytest.raises(Exception, match="conexão recusada"):
            ingest.store_embeddings(_make_docs())


class TestRunIngestion:
    def test_orchestrates_load_split_store_in_order(self, tmp_path, capsys):
        pdf_path = str(tmp_path / "doc.pdf")
        fake_docs = _make_docs()
        fake_chunks = _make_docs(n=5)

        with (
            patch.object(ingest, "load_pdf", return_value=fake_docs) as mock_load,
            patch.object(ingest, "split_documents", return_value=fake_chunks) as mock_split,
            patch.object(ingest, "store_embeddings") as mock_store,
        ):
            ingest.run_ingestion(pdf_path)

        mock_load.assert_called_once_with(pdf_path)
        mock_split.assert_called_once_with(fake_docs)
        mock_store.assert_called_once_with(fake_chunks)

        out = capsys.readouterr().out
        assert "Ingestão concluída com sucesso" in out
