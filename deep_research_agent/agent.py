"""ResearchAgent — wraps the Strands Agents SDK with a typed interface.

Insulates ResearchPipeline from Strands SDK internals.
Session context is injected into both the system prompt and log lines (Q3=C).
API keys are never included in prompts or logs (SECURITY-12).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator
from datetime import date
from typing import Any

from strands import Agent
from strands.models.bedrock import BedrockModel

from deep_research_agent.exceptions import BedrockError
from deep_research_agent.tools.tavily_tools import BaseTavilyTool
from deep_research_agent.types import AgentResponse, Source, TokenUsage, ToolCallRecord

logger = logging.getLogger(__name__)

# Tavily tool payloads carry their URLs under a different key per tool:
#   tavily_search  -> {"results":     [{"url", "title", "snippet", "score"}]}
#   tavily_extract -> {"extractions": [{"url", "content"}]}
#   tavily_crawl   -> {"pages":       [{"url", "depth", "content"}]}
_SOURCE_COLLECTIONS = ("results", "extractions", "pages")

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
        except Exception as exc:
            logger.error(
                "Bedrock invocation failed session_id=%s query_id=%s error=%s",
                session_context.get("session_id", ""),
                session_context.get("query_id", ""),
                type(exc).__name__,
            )
            raise BedrockError("Model invocation failed — please try again.") from exc

        # Response metadata is parsed outside the try above: a parsing failure here is a
        # defect in this class, not a model outage, and must not be reported as one.
        # Sources/tool calls come from the Agent's full conversation history (agent.messages),
        # NOT from the returned AgentResult — that object only carries the final `message`,
        # so reading result.messages would silently yield nothing.
        messages = getattr(agent, "messages", None) or []
        token_usage = self._extract_token_usage(result)
        sources = self._extract_sources(messages)
        tool_calls = self._extract_tool_calls(messages)

        if tool_calls and not sources:
            logger.warning(
                "Extracted %d tool call(s) but 0 sources session_id=%s query_id=%s "
                "— tool result payload shape may have changed.",
                len(tool_calls),
                session_context.get("session_id", ""),
                session_context.get("query_id", ""),
            )

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

    def _iter_content_blocks(self, messages: Any) -> Iterator[dict[str, Any]]:
        """Yield every content block across a list of conversation messages.

        Strands runs on the Bedrock Converse API, whose content blocks are keyed by
        type name — {"toolResult": {...}} / {"toolUse": {...}} — and carry no "type"
        field. Matching on block["type"] (the Anthropic Messages API shape) silently
        matches nothing, which is how source extraction previously always returned [].
        """
        for message in messages or []:
            if not isinstance(message, dict):
                continue
            for block in message.get("content") or []:
                if isinstance(block, dict):
                    yield block

    def _extract_sources(self, messages: Any) -> list[Source]:
        """Collect every source URL the Tavily tools returned, deduped, in first-seen order.

        `messages` is the Agent's full conversation history (agent.messages). These are the
        sources the agent *retrieved*, a superset of the ones it actually cited — the model
        may read a page and not use it.
        """
        sources: list[Source] = []
        seen: set[str] = set()

        for block in self._iter_content_blocks(messages):
            tool_result = block.get("toolResult")
            if not isinstance(tool_result, dict):
                continue
            for item in tool_result.get("content") or []:
                if not isinstance(item, dict):
                    continue
                # A tool result carries its payload as "text" (our tools return a JSON
                # string) or as already-decoded "json".
                payload = item.get("text") if "text" in item else item.get("json")
                for source in self._parse_sources(payload):
                    if source.url not in seen:
                        seen.add(source.url)
                        sources.append(source)

        return sources

    def _parse_sources(self, payload: Any) -> list[Source]:
        """Parse Source records out of one tool result payload.

        Handles all three Tavily tool response shapes (see _SOURCE_COLLECTIONS).
        Returns [] for anything unparseable rather than raising — a malformed payload
        from one tool should not lose the sources gathered from the others.
        """
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except (json.JSONDecodeError, ValueError):
                logger.debug("Tool result payload was not valid JSON; skipping.")
                return []
        else:
            data = payload

        if not isinstance(data, dict):
            return []

        sources: list[Source] = []
        for collection in _SOURCE_COLLECTIONS:
            for item in data.get(collection) or []:
                if not isinstance(item, dict):
                    continue
                url = item.get("url") or ""
                if url:
                    sources.append(Source(url=url, title=item.get("title") or url))
        return sources

    def _extract_tool_calls(self, messages: Any) -> list[ToolCallRecord]:
        """Record each tool invocation, pairing it with its result status by toolUseId."""
        statuses = self._collect_tool_statuses(messages)
        records: list[ToolCallRecord] = []

        for block in self._iter_content_blocks(messages):
            tool_use = block.get("toolUse")
            if not isinstance(tool_use, dict):
                continue
            records.append(
                ToolCallRecord(
                    tool_name=tool_use.get("name", "unknown"),
                    input_summary=str(tool_use.get("input", {}))[:200],
                    success=statuses.get(tool_use.get("toolUseId", ""), "success") == "success",
                    # The Converse API does not report per-tool latency; measuring it
                    # would require timing inside the tool layer itself.
                    latency_ms=0,
                )
            )
        return records

    def _collect_tool_statuses(self, messages: Any) -> dict[str, str]:
        """Map toolUseId -> result status ("success" | "error")."""
        statuses: dict[str, str] = {}
        for block in self._iter_content_blocks(messages):
            tool_result = block.get("toolResult")
            if isinstance(tool_result, dict):
                tool_use_id = tool_result.get("toolUseId", "")
                statuses[tool_use_id] = tool_result.get("status", "success")
        return statuses
