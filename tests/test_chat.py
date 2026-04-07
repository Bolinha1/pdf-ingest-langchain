import sys
from unittest.mock import MagicMock, patch
import pytest

# Inject mock for search module before chat imports it
sys.modules.setdefault("search", MagicMock())

import chat  # noqa: E402


class TestChatMain:
    def test_empty_input_does_not_call_answer_question(self, monkeypatch, capsys):
        inputs = iter(["", "exit"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        mock_answer = MagicMock(return_value="resposta")
        monkeypatch.setattr(chat, "answer_question", mock_answer)

        chat.main()

        mock_answer.assert_not_called()

    def test_exit_ends_loop_with_farewell(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "exit")
        monkeypatch.setattr(chat, "answer_question", MagicMock())

        chat.main()

        out = capsys.readouterr().out
        assert "Encerrando" in out

    def test_quit_ends_loop(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "quit")
        monkeypatch.setattr(chat, "answer_question", MagicMock())

        chat.main()

        out = capsys.readouterr().out
        assert "Encerrando" in out

    def test_ctrl_c_ends_loop_gracefully(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", MagicMock(side_effect=KeyboardInterrupt))
        monkeypatch.setattr(chat, "answer_question", MagicMock())

        chat.main()

        out = capsys.readouterr().out
        assert "Encerrando" in out

    def test_valid_input_displays_resposta_prefix(self, monkeypatch, capsys):
        inputs = iter(["Qual é o tema do documento?", "exit"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr(chat, "answer_question", lambda _: "O tema é tecnologia.")

        chat.main()

        out = capsys.readouterr().out
        assert "RESPOSTA:" in out
        assert "O tema é tecnologia." in out

    def test_multiple_questions_before_exit(self, monkeypatch, capsys):
        inputs = iter(["primeira pergunta", "segunda pergunta", "exit"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        mock_answer = MagicMock(return_value="alguma resposta")
        monkeypatch.setattr(chat, "answer_question", mock_answer)

        chat.main()

        assert mock_answer.call_count == 2
