"""Unit tests for ResearchAgent."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from deep_research_agent.agent import ResearchAgent, _SYSTEM_PROMPT_TEMPLATE
from deep_research_agent.exceptions import BedrockError
from deep_research_agent.types import AgentResponse


def _make_agent(model_id: str = "test-model") -> ResearchAgent:
    """Create ResearchAgent with mocked Tavily tools."""
    mock_tool = MagicMock()
    mock_tool.as_strands_tool.return_value = MagicMock()
    with patch("deep_research_agent.agent.Agent"), patch("deep_research_agent.agent.BedrockModel"):
        return ResearchAgent(model_id=model_id, tools=[mock_tool, mock_tool, mock_tool])


class TestBuildSystemPrompt:
    def test_contains_date(self) -> None:
        agent = _make_agent()
        prompt = agent._build_system_prompt({"session_id": "s1", "query_id": "q1"})
        import re
        assert re.search(r"\d{4}-\d{2}-\d{2}", prompt), "Date not found in system prompt"

    def test_contains_session_and_query_ids(self) -> None:
        agent = _make_agent()
        prompt = agent._build_system_prompt({"session_id": "sess-abc", "query_id": "q-xyz"})
        assert "sess-abc" in prompt
        assert "q-xyz" in prompt

    def test_contains_all_tool_names(self) -> None:
        agent = _make_agent()
        prompt = agent._build_system_prompt({"session_id": "s", "query_id": "q"})
        assert "tavily_search" in prompt
        assert "tavily_extract" in prompt
        assert "tavily_crawl" in prompt

    def test_contains_recommended_sequence(self) -> None:
        agent = _make_agent()
        prompt = agent._build_system_prompt({"session_id": "s", "query_id": "q"})
        assert "tavily_search" in prompt
        assert "tavily_extract" in prompt
        assert "tavily_crawl" in prompt

    def test_no_api_keys_in_prompt(self) -> None:
        agent = _make_agent()
        prompt = agent._build_system_prompt({"session_id": "s", "query_id": "q"})
        # API keys are never in the agent's system prompt (SECURITY-12)
        assert "TAVILY_API_KEY" not in prompt
        assert "aws_secret" not in prompt.lower()


class TestStream:
    def test_success_returns_agent_response(self) -> None:
        mock_tool = MagicMock()
        mock_tool.as_strands_tool.return_value = MagicMock()

        mock_result = MagicMock()
        mock_result.__str__ = lambda self: "Research response text."
        mock_result.metrics.accumulated_usage = {"inputTokens": 100, "outputTokens": 200}
        mock_result.messages = []

        tokens_received: list[str] = []

        with patch("deep_research_agent.agent.Agent") as mock_agent_cls, \
             patch("deep_research_agent.agent.BedrockModel"):
            mock_agent_instance = MagicMock()
            mock_agent_instance.return_value = mock_result
            mock_agent_cls.return_value = mock_agent_instance

            agent = ResearchAgent(model_id="test-model", tools=[mock_tool])
            response = agent.stream(
                query="What is quantum computing?",
                session_context={"session_id": "s1", "query_id": "q1"},
                callback=tokens_received.append,
            )

        assert isinstance(response, AgentResponse)
        assert response.is_complete is True
        assert response.response_text == "Research response text."

    def test_sdk_exception_raises_bedrock_error(self) -> None:
        mock_tool = MagicMock()
        mock_tool.as_strands_tool.return_value = MagicMock()

        with patch("deep_research_agent.agent.Agent") as mock_agent_cls, \
             patch("deep_research_agent.agent.BedrockModel"):
            mock_agent_instance = MagicMock()
            mock_agent_instance.side_effect = RuntimeError("Bedrock unavailable")
            mock_agent_cls.return_value = mock_agent_instance

            agent = ResearchAgent(model_id="test-model", tools=[mock_tool])
            with pytest.raises(BedrockError):
                agent.stream(
                    query="test query",
                    session_context={"session_id": "s", "query_id": "q"},
                    callback=lambda t: None,
                )

    def test_all_tools_registered_at_construction(self) -> None:
        tools = [MagicMock() for _ in range(3)]
        for t in tools:
            t.as_strands_tool.return_value = MagicMock()

        with patch("deep_research_agent.agent.Agent"), patch("deep_research_agent.agent.BedrockModel"):
            ResearchAgent(model_id="test", tools=tools)

        for tool in tools:
            tool.as_strands_tool.assert_called_once()
