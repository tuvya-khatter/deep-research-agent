"""Tavily tool integrations for the Deep Research Agent.

Three tools share a common base class and are registered with the Strands Agents SDK.
API keys are stored only as instance variables and are never logged (SECURITY-12).
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from tavily import TavilyClient

from deep_research_agent.exceptions import (
    TavilyCrawlError,
    TavilyExtractError,
    TavilySearchError,
)
from deep_research_agent.types import (
    CrawlResult,
    CrawledPage,
    ExtractionItem,
    ExtractResult,
    SearchItem,
    SearchResult,
)

logger = logging.getLogger(__name__)


@dataclass
class SearchInput:
    query: str
    max_results: int = 10


@dataclass
class ExtractInput:
    urls: list[str]


@dataclass
class CrawlInput:
    url: str
    max_depth: int = 2



class BaseTavilyTool(ABC):
    """Abstract base class for all Tavily tool integrations."""

    def __init__(self, api_key: str) -> None:
        self._client = TavilyClient(api_key=api_key)

    @abstractmethod
    def execute(self, input: Any) -> Any:
        """Execute the Tavily API call. Raises a TavilyError subclass on failure."""

    @abstractmethod
    def as_strands_tool(self) -> Any:
        """Return the Strands-decorated function for this tool."""


class TavilySearchTool(BaseTavilyTool):
    """Wraps the Tavily Search API as a Strands tool."""

    def __init__(self, api_key: str, max_results: int = 10) -> None:
        super().__init__(api_key)
        self._max_results = max_results

    def execute(self, input: SearchInput) -> SearchResult:
        """Call Tavily Search API. Raises TavilySearchError on failure."""
        try:
            raw = self._client.search(
                query=input.query,
                max_results=input.max_results,
            )
            items = [
                SearchItem(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    snippet=r.get("content", ""),
                    score=float(r.get("score", 0.0)),
                )
                for r in raw.get("results", [])
            ]
            return SearchResult(results=items)
        except Exception as exc:
            logger.warning("Tavily Search failed: %s", type(exc).__name__)
            raise TavilySearchError("Web search unavailable — please try again.") from exc

    def as_strands_tool(self) -> Any:
        tool_instance = self

        from strands import tool as strands_tool

        @strands_tool
        def tavily_search(query: str, max_results: int = 10) -> str:
            """Search the web for information on any topic using Tavily Search.

            Args:
                query: The search query string
                max_results: Maximum number of results to return (default: 10)

            Returns:
                JSON with search results containing url, title, and snippet for each result
            """
            result = tool_instance.execute(
                SearchInput(query=query, max_results=max_results or tool_instance._max_results)
            )
            return json.dumps(
                {
                    "results": [
                        {"url": r.url, "title": r.title, "snippet": r.snippet, "score": r.score}
                        for r in result.results
                    ]
                }
            )

        return tavily_search


class TavilyExtractTool(BaseTavilyTool):
    """Wraps the Tavily Extract API as a Strands tool.

    Retries each failed URL once before marking it as failed (RULE-TAVILY-02).
    Returns partial results when some URLs succeed. Raises TavilyExtractError
    only when ALL URLs fail.
    """

    def execute(self, input: ExtractInput) -> ExtractResult:
        """Call Tavily Extract API with per-URL retry. Returns partial results."""
        successful: list[ExtractionItem] = []
        failed_urls: list[str] = []

        for url in input.urls:
            item = self._extract_url_with_retry(url)
            if item is not None:
                successful.append(item)
            else:
                failed_urls.append(url)

        if failed_urls:
            logger.warning("Tavily Extract: %d URL(s) failed: %s", len(failed_urls), failed_urls)

        if not successful and input.urls:
            raise TavilyExtractError(
                "Content extraction unavailable — all URLs failed to extract."
            )

        return ExtractResult(extractions=successful)

    def _extract_url_with_retry(self, url: str) -> ExtractionItem | None:
        for attempt in range(2):
            try:
                raw = self._client.extract(urls=[url])
                results = raw.get("results", [])
                if results:
                    r = results[0]
                    return ExtractionItem(
                        url=r.get("url", url),
                        content=r.get("raw_content", ""),
                        metadata={},
                    )
                return None
            except Exception as exc:
                if attempt == 0:
                    logger.debug("Extract attempt 1 failed for %s: %s", url, type(exc).__name__)
                else:
                    logger.warning(
                        "Extract attempt 2 failed for %s: %s", url, type(exc).__name__
                    )
        return None

    def as_strands_tool(self) -> Any:
        tool_instance = self

        from strands import tool as strands_tool

        @strands_tool
        def tavily_extract(urls: list[str]) -> str:
            """Extract full page content from specific URLs using Tavily Extract.

            Args:
                urls: List of URLs to extract content from

            Returns:
                JSON with extracted content for each successfully processed URL
            """
            result = tool_instance.execute(ExtractInput(urls=urls))
            return json.dumps(
                {
                    "extractions": [
                        {"url": e.url, "content": e.content[:5000]}
                        for e in result.extractions
                    ]
                }
            )

        return tavily_extract


class TavilyCrawlTool(BaseTavilyTool):
    """Wraps the Tavily Crawl API as a Strands tool."""

    def __init__(self, api_key: str, max_depth: int = 2) -> None:
        super().__init__(api_key)
        self._max_depth = max_depth

    def execute(self, input: CrawlInput) -> CrawlResult:
        """Call Tavily Crawl API. Raises TavilyCrawlError on failure."""
        try:
            raw = self._client.crawl(url=input.url, max_depth=input.max_depth)
            pages = [
                CrawledPage(
                    url=p.get("url", ""),
                    content=p.get("raw_content", ""),
                    depth=p.get("depth", 0),
                )
                for p in raw.get("results", [])
            ]
            return CrawlResult(pages=pages)
        except Exception as exc:
            logger.warning("Tavily Crawl failed for %s: %s", input.url, type(exc).__name__)
            raise TavilyCrawlError("Web crawl unavailable — please try again.") from exc

    def as_strands_tool(self) -> Any:
        tool_instance = self

        from strands import tool as strands_tool

        @strands_tool
        def tavily_crawl(url: str, max_depth: int = 2) -> str:
            """Deep-crawl a website to explore linked pages using Tavily Crawl.

            Args:
                url: The starting URL to crawl
                max_depth: How many link-levels deep to crawl (default: 2)

            Returns:
                JSON with content from each crawled page and its depth level
            """
            result = tool_instance.execute(
                CrawlInput(url=url, max_depth=max_depth or tool_instance._max_depth)
            )
            return json.dumps(
                {
                    "pages": [
                        {"url": p.url, "depth": p.depth, "content": p.content[:3000]}
                        for p in result.pages
                    ]
                }
            )

        return tavily_crawl
