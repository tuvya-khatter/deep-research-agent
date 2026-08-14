"""CLI — interactive REPL loop for the Deep Research Agent.

Responsibilities: user input, query validation, streaming display, exit handling,
error display, and retry/skip prompting. Does not own research logic.

Rules implemented:
- RULE-QV-01/02/03/04: query validation
- RULE-EXIT-01/02: exit command detection
- RULE-ERR-01/02/03: error recovery and retry/skip
- RULE-STREAM-01/02: line-buffered display
- SECURITY-09: generic user-facing error messages only
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from deep_research_agent.exceptions import ResearchAgentError
from deep_research_agent.pipeline import ResearchPipeline
from deep_research_agent.session import SessionManager
from deep_research_agent.types import ResearchResult

logger = logging.getLogger(__name__)

_EXIT_COMMANDS = {"exit", "quit", "q"}
_BANNER = """
╔══════════════════════════════════════════════╗
║         Deep Research Agent  v0.1.0          ║
║  Type your research query and press Enter.   ║
║  Commands: exit / quit / q / Ctrl+D to quit  ║
╚══════════════════════════════════════════════╝
"""


class CLI:
    """Interactive REPL for the Deep Research Agent."""

    def __init__(self, pipeline: ResearchPipeline, session_manager: SessionManager) -> None:
        self._pipeline = pipeline
        self._session_manager = session_manager
        self._line_buffer: list[str] = []

    def run(self, model_id: str, output_dir: Path) -> None:
        """Start the REPL loop. Blocks until the user exits."""
        print(_BANNER)
        session = self._session_manager.start_session()
        logger.info("Session started session_id=%s", session.session_id)

        try:
            self._repl(session, model_id, output_dir)
        except KeyboardInterrupt:
            print("\nSession interrupted. Goodbye.")
        finally:
            self._session_manager.end_session(session)
            logger.info("Session ended session_id=%s", session.session_id)

    def _repl(self, session: object, model_id: str, output_dir: Path) -> None:
        from deep_research_agent.session import Session

        assert isinstance(session, Session)
        pending_retry: str | None = None

        while True:
            if pending_retry is not None:
                query = pending_retry
                pending_retry = None
            else:
                raw = self._get_query()
                if raw is None:
                    print("\nGoodbye.")
                    break
                if raw.strip().lower() in _EXIT_COMMANDS:
                    print("Goodbye.")
                    break
                try:
                    query = self._validate_query(raw)
                except ValueError as exc:
                    print(f"  ✗ {exc}")
                    continue

            query_record = self._session_manager.add_query(session, query)
            session_ctx = self._session_manager.to_context_dict(session, query_record)

            try:
                result = self._execute(query, session_ctx, output_dir, model_id)
                self._display_output_path(result.output_path)

            except ResearchAgentError as err:
                self._flush_line_buffer()
                self._display_error(err)
                choice = self._prompt_retry_or_skip()
                if choice == "retry":
                    pending_retry = query

    def _execute(
        self,
        query: str,
        session_ctx: dict[str, str],
        output_dir: Path,
        model_id: str,
    ) -> ResearchResult:
        """Run one query, streaming the report line-by-line to stdout."""
        result = self._pipeline.run(
            query=query,
            session_context=session_ctx,
            output_dir=output_dir,
            stream_callback=self._display_stream,
            model_id=model_id,
        )
        self._flush_line_buffer()
        self._display_separator()
        return result

    def _get_query(self) -> str | None:
        try:
            return input("\n> Research query: ").strip()
        except EOFError:
            return None

    def _validate_query(self, query: str) -> str:
        """Validate and return the stripped query (RULE-QV-01/02/03/04)."""
        stripped = query.strip()

        if not stripped:
            raise ValueError("Query cannot be empty.")

        if not any(c.isalnum() for c in stripped):
            raise ValueError("Query must contain at least one letter or number.")

        if stripped == stripped.upper() and stripped.replace(" ", "").isalpha() and " " not in stripped:
            raise ValueError(
                "That looks like a command. If this is your query, please add more context."
            )

        return stripped

    def _display_stream(self, token: str) -> None:
        """Accumulate tokens and flush line-by-line (RULE-STREAM-01)."""
        self._line_buffer.append(token)
        combined = "".join(self._line_buffer)
        while "\n" in combined:
            idx = combined.index("\n")
            line = combined[: idx + 1]
            print(line, end="", flush=True)
            combined = combined[idx + 1 :]
        self._line_buffer = [combined] if combined else []

    def _flush_line_buffer(self) -> None:
        """Flush any remaining content in the line buffer."""
        if self._line_buffer:
            print("".join(self._line_buffer), end="", flush=True)
            self._line_buffer = []

    def _display_separator(self) -> None:
        print("\n" + "─" * 60)

    def _display_output_path(self, path: Path) -> None:
        print(f"  ✓ Saved to: {path}")

    def _display_error(self, err: ResearchAgentError) -> None:
        """Display a generic user-facing error message (RULE-ERR-03, SECURITY-09)."""
        print(f"\n  ✗ {err.message}")

    def _prompt_retry_or_skip(self) -> str:
        """Prompt user to retry or skip after an error (RULE-ERR-02)."""
        try:
            choice = input("  Retry this query? [r=retry / s=skip]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "skip"
        return "retry" if choice in {"r", "retry"} else "skip"
