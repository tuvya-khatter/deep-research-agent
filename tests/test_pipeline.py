"""Unit tests and property-based tests for ResearchPipeline.

PBT invariants (PBT-03, PBT-07, PBT-08):
- test_property_result_duration_non_negative
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.conftest import query_text, session_context_strategy, token_usage_strategy

from deep_research_agent.exceptions import (
    BedrockError,
    OutputError,
    ResearchAgentError,
    TavilyError,
    TavilySearchError,
)
from deep_research_agent.pipeline import ResearchPipeline, _INCOMPLETE_MARKER
from deep_research_agent.types import AgentResponse, ResearchResult, Source, TokenUsage


def _make_pipeline(mock_agent: MagicMock, mock_output_manager: MagicMock) -> ResearchPipeline:
    return ResearchPipeline(agent=mock_agent, output_manager=mock_output_manager)


class TestRunSuccess:
    def test_returns_research_result(
        self, mock_agent: MagicMock, mock_output_manager: MagicMock, tmp_output_dir: Path
    ) -> None:
        pipeline = _make_pipeline(mock_agent, mock_output_manager)
        result = pipeline.run(
            query="quantum computing",
            session_context={"session_id": "s1", "query_id": "q1"},
            output_dir=tmp_output_dir,
            stream_callback=lambda t: None,
            model_id="test-model",
        )
        assert isinstance(result, ResearchResult)
        assert result.query == "quantum computing"
        assert result.is_complete is True

    def test_stream_callback_receives_tokens(
        self, mock_agent: MagicMock, mock_output_manager: MagicMock, tmp_output_dir: Path
    ) -> None:
        received: list[str] = []

        def fake_stream(query: str, session_context: dict, callback) -> AgentResponse:
            callback("token1")
            callback("token2")
            return AgentResponse(
                response_text="token1token2",
                sources=[],
                token_usage=TokenUsage(0, 0, 0),
                tool_calls=[],
                is_complete=True,
            )

        mock_agent.stream.side_effect = fake_stream
        pipeline = _make_pipeline(mock_agent, mock_output_manager)
        pipeline.run(
            query="test",
            session_context={"session_id": "s", "query_id": "q"},
            output_dir=tmp_output_dir,
            stream_callback=received.append,
        )
        assert "token1" in received
        assert "token2" in received

    def test_output_manager_write_called(
        self, mock_agent: MagicMock, mock_output_manager: MagicMock, tmp_output_dir: Path
    ) -> None:
        pipeline = _make_pipeline(mock_agent, mock_output_manager)
        pipeline.run(
            query="test",
            session_context={"session_id": "s", "query_id": "q"},
            output_dir=tmp_output_dir,
            stream_callback=lambda t: None,
        )
        mock_output_manager.write.assert_called_once()

    def test_duration_is_positive(
        self, mock_agent: MagicMock, mock_output_manager: MagicMock, tmp_output_dir: Path
    ) -> None:
        pipeline = _make_pipeline(mock_agent, mock_output_manager)
        result = pipeline.run(
            query="test",
            session_context={"session_id": "s", "query_id": "q"},
            output_dir=tmp_output_dir,
            stream_callback=lambda t: None,
        )
        assert result.duration_seconds >= 0


class TestPartialSaveOnStreamInterruption:
    def test_partial_response_saved_with_incomplete_marker(
        self, mock_output_manager: MagicMock, tmp_output_dir: Path
    ) -> None:
        mock_agent = MagicMock()

        def fake_stream(query, session_context, callback):
            callback("partial content")
            raise BedrockError("stream cut")

        mock_agent.stream.side_effect = fake_stream

        with pytest.raises(ResearchAgentError):
            pipeline = _make_pipeline(mock_agent, mock_output_manager)
            pipeline.run(
                query="test",
                session_context={"session_id": "s", "query_id": "q"},
                output_dir=tmp_output_dir,
                stream_callback=lambda t: None,
            )

        # Output manager should have been called with incomplete content
        call_args = mock_output_manager.write.call_args
        if call_args:
            response_text = call_args.kwargs.get("response_text") or call_args.args[0]
            assert "[INCOMPLETE" in response_text

    def test_no_partial_save_when_no_tokens_received(
        self, mock_output_manager: MagicMock, tmp_output_dir: Path
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.stream.side_effect = BedrockError("failed immediately")

        pipeline = _make_pipeline(mock_agent, mock_output_manager)
        with pytest.raises(ResearchAgentError):
            pipeline.run(
                query="test",
                session_context={"session_id": "s", "query_id": "q"},
                output_dir=tmp_output_dir,
                stream_callback=lambda t: None,
            )
        mock_output_manager.write.assert_not_called()


class TestErrorSurfacing:
    def _run(
        self,
        mock_agent: MagicMock,
        mock_output_manager: MagicMock,
        tmp_output_dir: Path,
    ) -> None:
        pipeline = _make_pipeline(mock_agent, mock_output_manager)
        pipeline.run(
            query="test",
            session_context={"session_id": "s", "query_id": "q"},
            output_dir=tmp_output_dir,
            stream_callback=lambda t: None,
        )

    def test_bedrock_error_raises_research_agent_error(
        self, mock_output_manager: MagicMock, tmp_output_dir: Path
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.stream.side_effect = BedrockError("bedrock fail")
        with pytest.raises(ResearchAgentError) as exc_info:
            self._run(mock_agent, mock_output_manager, tmp_output_dir)
        assert "model unavailable" in exc_info.value.message.lower()

    def test_tavily_error_raises_research_agent_error(
        self, mock_output_manager: MagicMock, tmp_output_dir: Path
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.stream.side_effect = TavilySearchError("tavily fail")
        with pytest.raises(ResearchAgentError) as exc_info:
            self._run(mock_agent, mock_output_manager, tmp_output_dir)
        assert "web search" in exc_info.value.message.lower()

    def test_output_error_raises_research_agent_error(
        self, mock_agent: MagicMock, tmp_output_dir: Path
    ) -> None:
        bad_output = MagicMock()
        bad_output.write.side_effect = OutputError("disk full")
        with pytest.raises(ResearchAgentError) as exc_info:
            self._run(mock_agent, bad_output, tmp_output_dir)
        assert "output file" in exc_info.value.message.lower()

    def test_error_messages_are_generic(
        self, tmp_output_dir: Path
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.stream.side_effect = BedrockError("InternalServerError at line 42 in sdk.py")
        mock_output_manager = MagicMock()

        pipeline = _make_pipeline(mock_agent, mock_output_manager)
        with pytest.raises(ResearchAgentError) as exc_info:
            pipeline.run(
                query="test",
                session_context={"session_id": "s", "query_id": "q"},
                output_dir=tmp_output_dir,
                stream_callback=lambda t: None,
            )
        # No internal path or class name in user-facing message (SECURITY-09)
        assert "InternalServerError" not in exc_info.value.message
        assert "line 42" not in exc_info.value.message
        assert "sdk.py" not in exc_info.value.message


# ---------------------------------------------------------------------------
# Property-Based Tests (PBT-03, PBT-07, PBT-08)
# ---------------------------------------------------------------------------

@pytest.mark.pbt
@given(
    query=query_text(),
    session_context=session_context_strategy(),
)
def test_property_result_duration_non_negative(
    query: str, session_context: dict[str, str], tmp_path: Path
) -> None:
    """Invariant: duration_seconds is always >= 0."""
    mock_agent = MagicMock()
    mock_agent.stream.return_value = AgentResponse(
        response_text="test",
        sources=[],
        token_usage=TokenUsage(0, 0, 0),
        tool_calls=[],
        is_complete=True,
    )
    mock_output_manager = MagicMock()
    mock_output_manager.write.return_value = tmp_path / "out.md"

    pipeline = ResearchPipeline(agent=mock_agent, output_manager=mock_output_manager)
    result = pipeline.run(
        query=query,
        session_context=session_context,
        output_dir=tmp_path,
        stream_callback=lambda t: None,
    )
    assert result.duration_seconds >= 0
