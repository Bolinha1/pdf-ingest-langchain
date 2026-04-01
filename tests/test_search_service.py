import sys
from unittest.mock import MagicMock, patch
import pytest

# Garante que config.settings esteja em sys.modules antes do import do SUT
sys.modules.setdefault("config", MagicMock())
sys.modules.setdefault("config.settings", MagicMock())

from services import search_service  # noqa: E402
from langchain_core.documents import Document  # noqa: E402


def _make_chunks(n=3):
    return [
        (Document(page_content=f"conteúdo do chunk {i}"), 0.9 - i * 0.1)
        for i in range(n)
    ]


@pytest.fixture
def mock_vs():
    with patch.object(search_service, "vector_store") as m:
        yield m


@pytest.fixture
def mock_llm():
    with patch.object(search_service, "llm") as m:
        yield m


class TestSearchChunks:
    def test_calls_similarity_search_with_k10(self, mock_vs):
        mock_vs.similarity_search_with_score.return_value = _make_chunks()

        search_service.search_chunks("qual é o tema?")

        mock_vs.similarity_search_with_score.assert_called_once_with("qual é o tema?", k=10)

    def test_raises_for_empty_query(self):
        with pytest.raises(ValueError):
            search_service.search_chunks("")

    def test_raises_for_whitespace_only_query(self):
        with pytest.raises(ValueError):
            search_service.search_chunks("   ")


class TestBuildPrompt:
    def test_contains_context_and_query(self):
        chunks = _make_chunks(2)
        prompt = search_service.build_prompt("qual o faturamento?", chunks)

        assert "conteúdo do chunk 0" in prompt
        assert "conteúdo do chunk 1" in prompt
        assert "qual o faturamento?" in prompt

    def test_chunks_separated_by_delimiter(self):
        chunks = _make_chunks(2)
        prompt = search_service.build_prompt("pergunta", chunks)

        assert "---" in prompt

    def test_contains_required_template_sections(self):
        chunks = _make_chunks()
        prompt = search_service.build_prompt("pergunta", chunks)

        assert "CONTEXTO:" in prompt
        assert "REGRAS:" in prompt
        assert "PERGUNTA DO USUÁRIO:" in prompt
        assert "RESPONDA A" in prompt

    def test_raises_for_empty_chunks(self):
        with pytest.raises(ValueError):
            search_service.build_prompt("pergunta", [])


class TestAskLlm:
    def test_returns_content_from_llm_response(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "resposta da LLM"
        mock_llm.invoke.return_value = mock_response

        result = search_service.ask_llm("prompt qualquer")

        assert result == "resposta da LLM"
        mock_llm.invoke.assert_called_once_with("prompt qualquer")


class TestAnswerQuestion:
    def test_returns_string_response(self, mock_vs, mock_llm):
        mock_vs.similarity_search_with_score.return_value = _make_chunks()
        mock_response = MagicMock()
        mock_response.content = "resposta final"
        mock_llm.invoke.return_value = mock_response

        result = search_service.answer_question("qual o tema?")

        assert result == "resposta final"

    def test_returns_friendly_message_on_internal_error(self, mock_vs):
        mock_vs.similarity_search_with_score.side_effect = Exception("falha")

        result = search_service.answer_question("qual o tema?")

        assert isinstance(result, str)
        assert len(result) > 0
