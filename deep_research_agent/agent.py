"""ResearchAgent — wraps the Strands Agents SDK with a typed interface.

Insulates ResearchPipeline from Strands SDK internals.
Session context is injected into both the system prompt and log lines (Q3=C).
API keys are never included in prompts or logs (SECURITY-12).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date
from typing import Any

from strands import Agent
from strands.models.bedrock import BedrockModel

from deep_research_agent.exceptions import BedrockError
from deep_research_agent.tools.tavily_tools import BaseTavilyTool
from deep_research_agent.types import AgentResponse, Source, TokenUsage, ToolCallRecord

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_TEMPLATE = """\
You are a deep research assistant with access to web research tools.

Date: {date}
Session ID: {session_id}
Query ID: {query_id}

Available tools:
- tavily_search:  Search the web for relevant sources on any topic
- tavily_extract: Extract full page content from specific URLs
- tavily_crawl:   Deep-crawl a site to explore linked pages in depth

Recommended research approach (adapt as the query requires):
1. Begin with tavily_search to identify the most relevant sources
2. Use tavily_extract on the top results to obtain full content
3. Use tavily_crawl when deep exploration of a specific domain is needed

Produce a comprehensive, well-cited research response in Markdown format.
Structure your response with clear headers and sections.
Cite sources inline and include URLs where relevant.\
"""


class ResearchAgent:
    """Strands Agents SDK façade providing a typed streaming interface."""

    def __init__(self, model_id: str, tools: list[BaseTavilyTool]) -> None:
        self._model_id = model_id
        self._strands_tools = [t.as_strands_tool() for t in tools]

    def stream(
        self,
        query: str,
        session_context: dict[str, str],
        callback: Callable[[str], None],
    ) -> AgentResponse:
        """Invoke the Strands agent with streaming. Returns a typed AgentResponse.

        Raises BedrockError on LLM or SDK failure.
        """
        system_prompt = self._build_system_prompt(session_context)
        sources: list[Source] = []
        tool_calls: list[ToolCallRecord] = []

        def callback_handler(**kwargs: Any) -> None:
            # Forward text tokens to the pipeline callback
            if "data" in kwargs:
                callback(kwargs["data"])

        agent = Agent(
            model=BedrockModel(model_id=self._model_id),
            tools=self._strands_tools,
            system_prompt=system_prompt,
            callback_handler=callback_handler,
        )

        try:
            result = agent(query)
            response_text = str(result)
            token_usage = self._extract_token_usage(result)
            sources = self._extract_sources(result)
            tool_calls = self._extract_tool_calls(result)
        except Exception as exc:
            logger.error(
                "Bedrock invocation failed session_id=%s query_id=%s error=%s",
                session_context.get("session_id", ""),
                session_context.get("query_id", ""),
                type(exc).__name__,
            )
            raise BedrockError("Model invocation failed — please try again.") from exc

        return AgentResponse(
            response_text=response_text,
            sources=sources,
            token_usage=token_usage,
            tool_calls=tool_calls,
            is_complete=True,
        )

    def _build_system_prompt(self, session_context: dict[str, str]) -> str:
        return _SYSTEM_PROMPT_TEMPLATE.format(
            date=date.today().isoformat(),
            session_id=session_context.get("session_id", ""),
            query_id=session_context.get("query_id", ""),
        )

    def _extract_token_usage(self, result: Any) -> TokenUsage:
        try:
            usage = result.metrics.accumulated_usage
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)
            return TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            )
        except Exception:
            return TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0)

    def _extract_sources(self, result: Any) -> list[Source]:
        """Extract cited sources from Strands tool call results."""
        sources: list[Source] = []
        try:
            for msg in getattr(result, "messages", []):
                for block in msg.get("content", []):
                    if block.get("type") == "tool_result":
                        for inner in block.get("content", []):
                            if inner.get("type") == "text":
                                text = inner.get("text", "")
                                sources.extend(self._parse_sources_from_json(text))
        except Exception:
            pass
        return sources

    def _parse_sources_from_json(self, text: str) -> list[Source]:
        import json

        sources: list[Source] = []
        try:
            data = json.loads(text)
            for item in data.get("results", []):
                url = item.get("url", "")
                title = item.get("title", url)
                if url:
                    sources.append(Source(url=url, title=title))
        except Exception:
            pass
        return sources

    def _extract_tool_calls(self, result: Any) -> list[ToolCallRecord]:
        records: list[ToolCallRecord] = []
        try:
            for msg in getattr(result, "messages", []):
                for block in msg.get("content", []):
                    if block.get("type") == "tool_use":
                        records.append(
                            ToolCallRecord(
                                tool_name=block.get("name", "unknown"),
                                input_summary=str(block.get("input", {}))[:200],
                                success=True,
                                latency_ms=0,
                            )
                        )
        except Exception:
            pass
        return records
