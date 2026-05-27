"""Unit tests for the Tavily tool layer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from deep_research_agent.exceptions import TavilyCrawlError, TavilyExtractError, TavilySearchError
from deep_research_agent.tools.tavily_tools import (
    BaseTavilyTool,
    CrawlInput,
    ExtractInput,
    SearchInput,
    TavilyCrawlTool,
    TavilyExtractTool,
    TavilySearchTool,
)
from deep_research_agent.types import CrawlResult, ExtractResult, SearchResult


# ---------------------------------------------------------------------------
# BaseTavilyTool
# ---------------------------------------------------------------------------

def test_base_tavily_tool_cannot_be_instantiated(tavily_api_key: str) -> None:
    with pytest.raises(TypeError):
        BaseTavilyTool(api_key=tavily_api_key)  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# TavilySearchTool
# ---------------------------------------------------------------------------

class TestTavilySearchTool:
    def _make_tool(self, api_key: str, max_results: int = 10) -> TavilySearchTool:
        with patch("deep_research_agent.tools.tavily_tools.TavilyClient"):
            tool = TavilySearchTool(api_key=api_key, max_results=max_results)
        return tool

    def test_execute_success(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key)
        tool._client.search.return_value = {
            "results": [
                {"url": "https://a.com", "title": "A", "content": "snippet A", "score": 0.9},
                {"url": "https://b.com", "title": "B", "content": "snippet B", "score": 0.7},
            ]
        }
        result = tool.execute(SearchInput(query="quantum computing", max_results=10))
        assert isinstance(result, SearchResult)
        assert len(result.results) == 2
        assert result.results[0].url == "https://a.com"

    def test_execute_raises_on_api_failure(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key)
        tool._client.search.side_effect = Exception("network error")
        with pytest.raises(TavilySearchError):
            tool.execute(SearchInput(query="test", max_results=5))

    def test_uses_instance_max_results(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key, max_results=15)
        assert tool._max_results == 15

    def test_as_strands_tool_returns_callable(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key)
        strands_fn = tool.as_strands_tool()
        assert callable(strands_fn)


# ---------------------------------------------------------------------------
# TavilyExtractTool — retry logic (RULE-TAVILY-02)
# ---------------------------------------------------------------------------

class TestTavilyExtractTool:
    def _make_tool(self, api_key: str) -> TavilyExtractTool:
        with patch("deep_research_agent.tools.tavily_tools.TavilyClient"):
            tool = TavilyExtractTool(api_key=api_key)
        return tool

    def test_execute_success_all_urls(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key)
        tool._client.extract.return_value = {
            "results": [{"url": "https://a.com", "raw_content": "full content"}]
        }
        result = tool.execute(ExtractInput(urls=["https://a.com"]))
        assert isinstance(result, ExtractResult)
        assert len(result.extractions) == 1
        assert result.extractions[0].url == "https://a.com"

    def test_retry_once_on_first_failure(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key)
        call_count = {"n": 0}

        def side_effect(urls: list[str]) -> dict:
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("first attempt fails")
            return {"results": [{"url": urls[0], "raw_content": "content"}]}

        tool._client.extract.side_effect = side_effect
        result = tool.execute(ExtractInput(urls=["https://a.com"]))
        assert len(result.extractions) == 1
        assert call_count["n"] == 2  # exactly 2 attempts

    def test_partial_results_when_some_urls_fail(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key)

        def side_effect(urls: list[str]) -> dict:
            if "fail" in urls[0]:
                raise Exception("this URL always fails")
            return {"results": [{"url": urls[0], "raw_content": "ok"}]}

        tool._client.extract.side_effect = side_effect
        result = tool.execute(
            ExtractInput(urls=["https://ok.com", "https://fail.com"])
        )
        assert len(result.extractions) == 1
        assert result.extractions[0].url == "https://ok.com"

    def test_raises_when_all_urls_fail(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key)
        tool._client.extract.side_effect = Exception("always fails")
        with pytest.raises(TavilyExtractError):
            tool.execute(ExtractInput(urls=["https://a.com", "https://b.com"]))

    def test_as_strands_tool_returns_callable(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key)
        assert callable(tool.as_strands_tool())


# ---------------------------------------------------------------------------
# TavilyCrawlTool
# ---------------------------------------------------------------------------

class TestTavilyCrawlTool:
    def _make_tool(self, api_key: str, max_depth: int = 2) -> TavilyCrawlTool:
        with patch("deep_research_agent.tools.tavily_tools.TavilyClient"):
            tool = TavilyCrawlTool(api_key=api_key, max_depth=max_depth)
        return tool

    def test_execute_success(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key)
        tool._client.crawl.return_value = {
            "results": [
                {"url": "https://a.com", "raw_content": "page content", "depth": 0},
                {"url": "https://a.com/sub", "raw_content": "sub content", "depth": 1},
            ]
        }
        result = tool.execute(CrawlInput(url="https://a.com", max_depth=2))
        assert isinstance(result, CrawlResult)
        assert len(result.pages) == 2
        assert result.pages[1].depth == 1

    def test_raises_on_api_failure(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key)
        tool._client.crawl.side_effect = Exception("crawl failed")
        with pytest.raises(TavilyCrawlError):
            tool.execute(CrawlInput(url="https://a.com", max_depth=2))

    def test_uses_instance_max_depth(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key, max_depth=3)
        assert tool._max_depth == 3

    def test_as_strands_tool_returns_callable(self, tavily_api_key: str) -> None:
        tool = self._make_tool(tavily_api_key)
        assert callable(tool.as_strands_tool())
