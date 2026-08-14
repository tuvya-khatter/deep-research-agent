"""Unit tests for ResearchAgent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from deep_research_agent.agent import ResearchAgent, _SYSTEM_PROMPT_TEMPLATE
from deep_research_agent.exceptions import BedrockError
from deep_research_agent.types import AgentResponse


def _tool_use(name: str, tool_use_id: str, **inputs: object) -> dict:
    """Build a Bedrock Converse toolUse content block."""
    return {"toolUse": {"name": name, "toolUseId": tool_use_id, "input": inputs}}


def _tool_result(tool_use_id: str, payload: object, status: str = "success") -> dict:
    """Build a Bedrock Converse toolResult block carrying a JSON string payload.

    This mirrors the real runtime shape: our Tavily tools return JSON strings, which
    Strands wraps as {"toolResult": {"content": [{"text": "..."}], "status": ...}}.
    """
    return {
        "toolResult": {
            "toolUseId": tool_use_id,
            "status": status,
            "content": [{"text": json.dumps(payload)}],
        }
    }


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


class TestExtractSources:
    """Source extraction against realistic Bedrock Converse message shapes.

    Regression guard: these previously used `messages = []`, so the extractor was never
    exercised and its Anthropic-format matching (block["type"] == "tool_result") went
    unnoticed while returning [] on every real run.
    """

    def test_extracts_sources_from_search_results(self) -> None:
        agent = _make_agent()
        messages = [
            {
                "role": "user",
                "content": [
                    _tool_result(
                        "t1",
                        {
                            "results": [
                                {"url": "https://a.example/x", "title": "Alpha", "score": 0.9},
                                {"url": "https://b.example/y", "title": "Beta", "score": 0.8},
                            ]
                        },
                    )
                ],
            }
        ]

        sources = agent._extract_sources(messages)

        assert [s.url for s in sources] == ["https://a.example/x", "https://b.example/y"]
        assert [s.title for s in sources] == ["Alpha", "Beta"]

    def test_extracts_sources_from_extract_and_crawl_shapes(self) -> None:
        """tavily_extract and tavily_crawl key their URLs differently from tavily_search."""
        agent = _make_agent()
        messages = [
            {
                "role": "user",
                "content": [
                    _tool_result("t1", {"extractions": [{"url": "https://e.example", "content": "..."}]}),
                    _tool_result("t2", {"pages": [{"url": "https://c.example", "depth": 1}]}),
                ],
            }
        ]

        urls = [s.url for s in agent._extract_sources(messages)]

        assert urls == ["https://e.example", "https://c.example"]

    def test_deduplicates_repeated_urls(self) -> None:
        agent = _make_agent()
        repeated = {"results": [{"url": "https://dup.example", "title": "Dup"}]}
        messages = [
            {"role": "user", "content": [_tool_result("t1", repeated), _tool_result("t2", repeated)]}
        ]

        assert len(agent._extract_sources(messages)) == 1

    def test_falls_back_to_url_when_title_missing(self) -> None:
        agent = _make_agent()
        messages = [
            {"role": "user", "content": [_tool_result("t1", {"results": [{"url": "https://n.example"}]})]}
        ]

        assert agent._extract_sources(messages)[0].title == "https://n.example"

    def test_malformed_payload_does_not_lose_other_sources(self) -> None:
        agent = _make_agent()
        messages = [
            {
                "role": "user",
                "content": [
                    {"toolResult": {"toolUseId": "t1", "status": "success", "content": [{"text": "not json"}]}},
                    _tool_result("t2", {"results": [{"url": "https://ok.example", "title": "OK"}]}),
                ],
            }
        ]

        assert [s.url for s in agent._extract_sources(messages)] == ["https://ok.example"]

    def test_no_messages_returns_empty(self) -> None:
        agent = _make_agent()

        assert agent._extract_sources([]) == []


class TestExtractToolCalls:
    def test_records_tool_use_blocks(self) -> None:
        agent = _make_agent()
        messages = [
            {"role": "assistant", "content": [_tool_use("tavily_search", "t1", query="quantum")]}
        ]

        calls = agent._extract_tool_calls(messages)

        assert len(calls) == 1
        assert calls[0].tool_name == "tavily_search"
        assert "quantum" in calls[0].input_summary
        assert calls[0].success is True

    def test_error_status_marks_call_unsuccessful(self) -> None:
        """success was previously hardcoded True regardless of the actual result."""
        agent = _make_agent()
        messages = [
            {"role": "assistant", "content": [_tool_use("tavily_crawl", "t1", url="https://x.example")]},
            {"role": "user", "content": [_tool_result("t1", {"pages": []}, status="error")]},
        ]

        assert agent._extract_tool_calls(messages)[0].success is False
