"""ResearchPipeline — owns the complete research lifecycle for one query.

Responsibilities:
- Invoke ResearchAgent with token accumulation for partial-save support (Q13)
- Write output via OutputManager
- Log structured result fields (RULE-LOG-01)
- Catch all errors and surface generic ResearchAgentError (RULE-ERR-03, SECURITY-09)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from deep_research_agent.agent import ResearchAgent
from deep_research_agent.exceptions import (
    BedrockError,
    OutputError,
    ResearchAgentError,
    TavilyError,
)
from deep_research_agent.output import OutputManager
from deep_research_agent.types import (
    AgentResponse,
    OutputMetadata,
    ResearchResult,
    Source,
    TokenUsage,
)

logger = logging.getLogger(__name__)

_INCOMPLETE_MARKER = "\n\n---\n**[INCOMPLETE — stream interrupted]**"


class ResearchPipeline:
    """Orchestrates the end-to-end research flow for a single query."""

    def __init__(self, agent: ResearchAgent, output_manager: OutputManager) -> None:
        self._agent = agent
        self._output_manager = output_manager

    def run(
        self,
        query: str,
        session_context: dict[str, str],
        output_dir: Path,
        stream_callback: Callable[[str], None],
        model_id: str = "",
    ) -> ResearchResult:
        """Run the full research pipeline. Streams tokens via stream_callback.

        Raises ResearchAgentError (generic message) on any failure.
        """
        start_time = time.monotonic()

        try:
            agent_response = self._invoke_agent(query, session_context, stream_callback)
            output_path = self._save_output(agent_response, query, output_dir, session_context, model_id)
            duration = time.monotonic() - start_time

            result = ResearchResult(
                query=query,
                response_text=agent_response.response_text,
                output_path=output_path,
                sources=agent_response.sources,
                token_usage=agent_response.token_usage,
                duration_seconds=round(duration, 2),
                session_id=session_context.get("session_id", ""),
                query_id=session_context.get("query_id", ""),
                is_complete=agent_response.is_complete,
            )
            self._log_result(result, model_id)
            return result

        except BedrockError:
            raise ResearchAgentError("Research failed — model unavailable. Please try again.")
        except TavilyError:
            raise ResearchAgentError(
                "Research failed — web search unavailable. Please try again."
            )
        except OutputError:
            raise ResearchAgentError(
                "Research failed — could not save output file. Check disk permissions."
            )
        except ResearchAgentError:
            raise
        except Exception as exc:
            logger.error(
                "Unexpected error in pipeline session_id=%s query_id=%s",
                session_context.get("session_id", ""),
                session_context.get("query_id", ""),
                exc_info=True,
            )
            raise ResearchAgentError("Research failed — unexpected error. Please try again.")

    def _invoke_agent(
        self,
        query: str,
        session_context: dict[str, str],
        stream_callback: Callable[[str], None],
    ) -> AgentResponse:
        """Invoke ResearchAgent with token accumulation for partial-save support (RULE-BEDROCK-01)."""
        token_buffer: list[str] = []

        def accumulating_callback(token: str) -> None:
            token_buffer.append(token)
            stream_callback(token)

        try:
            return self._agent.stream(query, session_context, accumulating_callback)
        except BedrockError:
            if token_buffer:
                partial_text = "".join(token_buffer) + _INCOMPLETE_MARKER
                logger.error(
                    "Bedrock stream interrupted after %d tokens; saving partial response.",
                    len(token_buffer),
                )
                return AgentResponse(
                    response_text=partial_text,
                    sources=[],
                    token_usage=TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0),
                    tool_calls=[],
                    is_complete=False,
                )
            raise

    def _save_output(
        self,
        response: AgentResponse,
        query: str,
        output_dir: Path,
        session_context: dict[str, str],
        model_id: str,
    ) -> Path:
        metadata = OutputMetadata(
            query=query,
            model_id=model_id,
            session_id=session_context.get("session_id", ""),
            query_id=session_context.get("query_id", ""),
            generated_at=datetime.now(tz=timezone.utc),
            source_count=len(response.sources),
        )
        return self._output_manager.write(
            response_text=response.response_text,
            query=query,
            sources=response.sources,
            metadata=metadata,
            output_dir=output_dir,
        )

    def _log_result(self, result: ResearchResult, model_id: str) -> None:
        """Log structured per-query result fields (RULE-LOG-01). No credentials logged."""
        logger.info(
            "query_complete query_id=%s session_id=%s model=%s "
            "input_tokens=%d output_tokens=%d total_tokens=%d "
            "duration_s=%.2f source_count=%d output=%s is_complete=%s",
            result.query_id,
            result.session_id,
            model_id,
            result.token_usage.input_tokens,
            result.token_usage.output_tokens,
            result.token_usage.total_tokens,
            result.duration_seconds,
            len(result.sources),
            result.output_path,
            result.is_complete,
        )
