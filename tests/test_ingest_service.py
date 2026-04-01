import sys
from unittest.mock import MagicMock, patch
import pytest

# Garante que config.settings esteja em sys.modules antes do import do SUT
sys.modules.setdefault("config", MagicMock())
sys.modules.setdefault("config.settings", MagicMock())

from services import ingest_service  # noqa: E402
from langchain_core.documents import Document  # noqa: E402


def _make_docs(n=3, content="texto de exemplo com mais de dez caracteres"):
    return [Document(page_content=content, metadata={"page": i}) for i in range(n)]


@pytest.fixture
def mock_vector_store():
    with patch.object(ingest_service, "vector_store") as m:
        yield m


class TestLoadPdf:
    def test_returns_documents_for_valid_pdf(self, tmp_path):
        pdf_file = tmp_path / "file.pdf"
        pdf_file.touch()  # precisa existir para passar no os.path.exists
        fake_docs = _make_docs()
        with patch("services.ingest_service.PyPDFLoader") as MockLoader:
            MockLoader.return_value.load.return_value = fake_docs
            result = ingest_service.load_pdf(str(pdf_file))

        assert result == fake_docs

    def test_raises_file_not_found_for_missing_path(self):
        with pytest.raises(FileNotFoundError):
            ingest_service.load_pdf("/caminho/inexistente/arquivo.pdf")


class TestSplitDocuments:
    def test_returns_chunks_for_valid_docs(self):
        long_text = "palavra " * 300  # ~2400 chars → deve gerar vários chunks
        docs = [Document(page_content=long_text)]
        chunks = ingest_service.split_documents(docs)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.page_content) <= 1000

    def test_raises_for_empty_list(self):
        with pytest.raises(ValueError):
            ingest_service.split_documents([])


class TestStoreEmbeddings:
    def test_calls_add_documents_with_chunks(self, mock_vector_store):
        chunks = _make_docs()
        ingest_service.store_embeddings(chunks)
        mock_vector_store.add_documents.assert_called_once_with(chunks)

    def test_raises_on_db_error(self, mock_vector_store):
        mock_vector_store.add_documents.side_effect = Exception("conexão recusada")
        with pytest.raises(Exception, match="conexão recusada"):
            ingest_service.store_embeddings(_make_docs())


class TestRunIngestion:
    def test_orchestrates_load_split_store_in_order(self, tmp_path, capsys):
        pdf_path = str(tmp_path / "doc.pdf")
        fake_docs = _make_docs()
        fake_chunks = _make_docs(n=5)

        with (
            patch.object(ingest_service, "load_pdf", return_value=fake_docs) as mock_load,
            patch.object(ingest_service, "split_documents", return_value=fake_chunks) as mock_split,
            patch.object(ingest_service, "store_embeddings") as mock_store,
        ):
            ingest_service.run_ingestion(pdf_path)

        mock_load.assert_called_once_with(pdf_path)
        mock_split.assert_called_once_with(fake_docs)
        mock_store.assert_called_once_with(fake_chunks)

        out = capsys.readouterr().out
        assert "Ingestão concluída com sucesso" in out
