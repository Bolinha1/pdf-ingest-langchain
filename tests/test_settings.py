import importlib
import os
import sys

import pytest
from unittest.mock import patch, MagicMock


def _clear_settings():
    for mod in list(sys.modules.keys()):
        if mod in ("config.settings", "config"):
            del sys.modules[mod]


@pytest.fixture(autouse=True)
def isolate_settings_module():
    _clear_settings()
    yield
    _clear_settings()


_VALID_ENV = {
    "OPENAI_API_KEY": "sk-test-key",
    "DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/testdb",
}


def test_instantiates_with_valid_env():
    with (
        patch.dict(os.environ, _VALID_ENV, clear=True),
        patch("dotenv.load_dotenv"),
        patch("langchain_openai.OpenAIEmbeddings", return_value=MagicMock()) as MockEmb,
        patch("langchain_openai.ChatOpenAI", return_value=MagicMock()) as MockLLM,
        patch("langchain_postgres.PGVector", return_value=MagicMock()) as MockPG,
    ):
        import config.settings as settings

        assert settings.embeddings is not None
        assert settings.llm is not None
        assert settings.vector_store is not None
        MockEmb.assert_called_once()
        MockLLM.assert_called_once()
        MockPG.assert_called_once()


def test_raises_without_api_key():
    env = {"DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/testdb"}
    with patch.dict(os.environ, env, clear=True), patch("dotenv.load_dotenv"):
        with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
            import config.settings


def test_raises_without_database_url():
    env = {"OPENAI_API_KEY": "sk-test-key"}
    with patch.dict(os.environ, env, clear=True), patch("dotenv.load_dotenv"):
        with pytest.raises(EnvironmentError, match="DATABASE_URL"):
            import config.settings
