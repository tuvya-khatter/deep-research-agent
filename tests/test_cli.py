"""Unit tests and property-based tests for the CLI.

PBT invariants (PBT-03, PBT-07, PBT-08):
- test_property_validate_query_valid_inputs_never_raise
- test_property_validate_query_empty_always_raises
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given

from tests.conftest import invalid_query_empty, query_text, single_word_all_caps

from deep_research_agent.cli import CLI, _EXIT_COMMANDS
from deep_research_agent.exceptions import ResearchAgentError
from deep_research_agent.session import SessionManager
from deep_research_agent.types import AgentResponse, ResearchResult, Source, TokenUsage


def _make_cli(pipeline: MagicMock | None = None) -> CLI:
    pipeline = pipeline or MagicMock()
    return CLI(pipeline=pipeline, session_manager=SessionManager())


class TestValidateQuery:
    def test_valid_query_returned_stripped(self) -> None:
        cli = _make_cli()
        assert cli._validate_query("  What is AI?  ") == "What is AI?"

    def test_empty_string_raises(self) -> None:
        cli = _make_cli()
        with pytest.raises(ValueError, match="empty"):
            cli._validate_query("")

    def test_whitespace_only_raises(self) -> None:
        cli = _make_cli()
        with pytest.raises(ValueError):
            cli._validate_query("   ")

    def test_no_alphanumeric_raises(self) -> None:
        cli = _make_cli()
        with pytest.raises(ValueError):
            cli._validate_query("!!!???")

    def test_single_word_all_caps_raises(self) -> None:
        cli = _make_cli()
        with pytest.raises(ValueError, match="command"):
            cli._validate_query("RESEARCH")

    def test_multi_word_all_caps_does_not_raise(self) -> None:
        cli = _make_cli()
        # Multi-word all-caps is not a command pattern
        result = cli._validate_query("QUANTUM COMPUTING")
        assert result == "QUANTUM COMPUTING"

    @pytest.mark.parametrize("cmd", list(_EXIT_COMMANDS))
    def test_exit_commands_are_valid_strings(self, cmd: str) -> None:
        cli = _make_cli()
        # Exit commands aren't validated by _validate_query (handled before)
        # but they are single lowercase words, so they pass validation
        result = cli._validate_query(cmd)
        assert result.lower() in _EXIT_COMMANDS


class TestGetQuery:
    def test_eof_returns_none(self) -> None:
        cli = _make_cli()
        with patch("builtins.input", side_effect=EOFError):
            assert cli._get_query() is None

    def test_normal_input_returned(self) -> None:
        cli = _make_cli()
        with patch("builtins.input", return_value="test query"):
            result = cli._get_query()
        assert result == "test query"


class TestDisplayStream:
    def test_line_buffer_flushes_on_newline(self, capsys) -> None:
        cli = _make_cli()
        cli._display_stream("hello\n")
        captured = capsys.readouterr()
        assert "hello\n" in captured.out

    def test_partial_token_buffered(self, capsys) -> None:
        cli = _make_cli()
        cli._display_stream("partial")
        captured = capsys.readouterr()
        assert captured.out == ""  # not yet flushed
        assert "partial" in "".join(cli._line_buffer)

    def test_flush_line_buffer_outputs_remaining(self, capsys) -> None:
        cli = _make_cli()
        cli._display_stream("buffered content")
        cli._flush_line_buffer()
        captured = capsys.readouterr()
        assert "buffered content" in captured.out

    def test_multi_line_token(self, capsys) -> None:
        cli = _make_cli()
        cli._display_stream("line1\nline2\npartial")
        captured = capsys.readouterr()
        assert "line1\n" in captured.out
        assert "line2\n" in captured.out


class TestPromptRetryOrSkip:
    def test_r_returns_retry(self) -> None:
        cli = _make_cli()
        with patch("builtins.input", return_value="r"):
            assert cli._prompt_retry_or_skip() == "retry"

    def test_retry_returns_retry(self) -> None:
        cli = _make_cli()
        with patch("builtins.input", return_value="retry"):
            assert cli._prompt_retry_or_skip() == "retry"

    def test_s_returns_skip(self) -> None:
        cli = _make_cli()
        with patch("builtins.input", return_value="s"):
            assert cli._prompt_retry_or_skip() == "skip"

    def test_other_returns_skip(self) -> None:
        cli = _make_cli()
        with patch("builtins.input", return_value="anything"):
            assert cli._prompt_retry_or_skip() == "skip"

    def test_eof_returns_skip(self) -> None:
        cli = _make_cli()
        with patch("builtins.input", side_effect=EOFError):
            assert cli._prompt_retry_or_skip() == "skip"


class TestDisplayError:
    def test_shows_message_only(self, capsys) -> None:
        cli = _make_cli()
        err = ResearchAgentError("Research failed — model unavailable.")
        cli._display_error(err)
        captured = capsys.readouterr()
        assert "Research failed" in captured.out
        assert "ResearchAgentError" not in captured.out


class TestRunLoop:
    def _make_result(self, tmp_path: Path) -> ResearchResult:
        return ResearchResult(
            query="test",
            response_text="response",
            output_path=tmp_path / "out.md",
            sources=[],
            token_usage=TokenUsage(100, 200, 300),
            duration_seconds=1.5,
            session_id="s1",
            query_id="q1",
        )

    def test_exit_command_ends_loop(self, tmp_path: Path) -> None:
        pipeline = MagicMock()
        cli = _make_cli(pipeline)
        inputs = iter(["exit"])
        with patch("builtins.input", side_effect=inputs):
            cli.run(model_id="test-model", output_dir=tmp_path)
        pipeline.run.assert_not_called()

    def test_query_submitted_to_pipeline(self, tmp_path: Path) -> None:
        pipeline = MagicMock()
        pipeline.run.return_value = self._make_result(tmp_path)
        cli = _make_cli(pipeline)
        inputs = iter(["What is AI?", "exit"])
        with patch("builtins.input", side_effect=inputs):
            cli.run(model_id="test-model", output_dir=tmp_path)
        pipeline.run.assert_called_once()
        call_kwargs = pipeline.run.call_args
        assert call_kwargs.kwargs.get("query") == "What is AI?" or call_kwargs.args[0] == "What is AI?"

    def test_error_triggers_retry_prompt(self, tmp_path: Path) -> None:
        pipeline = MagicMock()
        pipeline.run.side_effect = [
            ResearchAgentError("fail"),
            self._make_result(tmp_path),
        ]
        cli = _make_cli(pipeline)
        # First query fails → retry prompt → skip → next query → exit
        inputs = iter(["What is AI?", "s", "exit"])
        with patch("builtins.input", side_effect=inputs):
            cli.run(model_id="test-model", output_dir=tmp_path)
        # Called once (first attempt, then skipped)
        assert pipeline.run.call_count == 1


# ---------------------------------------------------------------------------
# Property-Based Tests (PBT-03, PBT-07, PBT-08)
# ---------------------------------------------------------------------------

@pytest.mark.pbt
@given(query=query_text())
def test_property_validate_query_valid_inputs_never_raise(query: str) -> None:
    """Invariant: valid queries (alphanumeric, not single all-caps) never raise ValueError."""
    cli = _make_cli()
    # query_text() strategy guarantees: non-empty, has alphanumeric, not single-word all-caps
    result = cli._validate_query(query)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.pbt
@given(query=invalid_query_empty())
def test_property_validate_query_empty_always_raises(query: str) -> None:
    """Invariant: empty or whitespace-only inputs always raise ValueError."""
    cli = _make_cli()
    with pytest.raises(ValueError):
        cli._validate_query(query)
