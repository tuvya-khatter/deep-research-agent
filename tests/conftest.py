"""Shared pytest fixtures and Hypothesis domain strategies.

Hypothesis strategies are centralised here for reusability (PBT-07).
All strategies produce domain-valid inputs respecting business constraints.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from hypothesis import settings
from hypothesis import strategies as st

from deep_research_agent.session import QueryRecord, Session
from deep_research_agent.types import (
    AgentResponse,
    OutputMetadata,
    ResearchResult,
    Source,
    TokenUsage,
    ToolCallRecord,
)

# ---------------------------------------------------------------------------
# Hypothesis settings
# ---------------------------------------------------------------------------

settings.register_profile("ci", max_examples=200)
settings.register_profile("default", max_examples=50)
settings.load_profile("default")


# ---------------------------------------------------------------------------
# Hypothesis domain strategies (PBT-07)
# ---------------------------------------------------------------------------

def query_text() -> st.SearchStrategy[str]:
    """Generate valid research query strings (non-empty, has alphanumeric chars,
    not single-word all-caps)."""
    return (
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Po")),
            min_size=1,
            max_size=500,
        )
        .filter(lambda s: s.strip() != "")
        .filter(lambda s: any(c.isalnum() for c in s))
        .filter(
            lambda s: not (
                s.strip() == s.strip().upper()
                and s.strip().replace(" ", "").isalpha()
                and " " not in s.strip()
            )
        )
    )


def invalid_query_empty() -> st.SearchStrategy[str]:
    """Generate strings that are empty or whitespace-only."""
    return st.one_of(
        st.just(""),
        st.text(alphabet=" \t\n\r", min_size=1, max_size=20),
    )


def single_word_all_caps() -> st.SearchStrategy[str]:
    """Generate single-word all-uppercase strings (command-like)."""
    return st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        min_size=2,
        max_size=20,
    ).filter(lambda s: " " not in s)


def valid_slug_input() -> st.SearchStrategy[str]:
    """Generate strings suitable for slug sanitization testing."""
    return st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Po", "Pd")),
        min_size=1,
        max_size=200,
    )


def source_strategy() -> st.SearchStrategy[Source]:
    """Generate valid Source objects."""
    return st.builds(
        Source,
        url=st.from_regex(r"https://[a-z]{3,10}\.[a-z]{2,4}/[a-z0-9/]{0,30}", fullmatch=True),
        title=st.text(min_size=1, max_size=100),
        description=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
    )


def source_list() -> st.SearchStrategy[list[Source]]:
    """Generate lists of valid Sources (0–10 items)."""
    return st.lists(source_strategy(), min_size=0, max_size=10)


def token_usage_strategy() -> st.SearchStrategy[TokenUsage]:
    """Generate valid TokenUsage objects with non-negative values."""
    return st.builds(
        TokenUsage,
        input_tokens=st.integers(min_value=0, max_value=100_000),
        output_tokens=st.integers(min_value=0, max_value=10_000),
        total_tokens=st.integers(min_value=0, max_value=110_000),
    )


def session_context_strategy() -> st.SearchStrategy[dict[str, str]]:
    """Generate valid session context dicts with UUID session/query IDs."""
    return st.fixed_dictionaries(
        {
            "session_id": st.uuids().map(str),
            "query_id": st.uuids().map(str),
        }
    )


def output_metadata_strategy() -> st.SearchStrategy[OutputMetadata]:
    """Generate valid OutputMetadata objects."""
    return st.builds(
        OutputMetadata,
        query=query_text(),
        model_id=st.just("us.anthropic.claude-3-7-sonnet-20250219-v1:0"),
        session_id=st.uuids().map(str),
        query_id=st.uuids().map(str),
        generated_at=st.just(datetime.now(tz=timezone.utc)),
        source_count=st.integers(min_value=0, max_value=50),
    )


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tavily_api_key() -> str:
    return "test-tavily-key-not-real"


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "research-output"
    d.mkdir()
    return d


@pytest.fixture
def sample_session() -> Session:
    return Session(
        session_id=str(uuid.uuid4()),
        start_time=datetime.now(tz=timezone.utc),
    )


@pytest.fixture
def sample_query_record() -> QueryRecord:
    return QueryRecord(
        query_id=str(uuid.uuid4()),
        query_text="What is quantum computing?",
        submitted_at=datetime.now(tz=timezone.utc),
    )


@pytest.fixture
def sample_sources() -> list[Source]:
    return [
        Source(url="https://example.com/a", title="Example A", description="First source"),
        Source(url="https://example.com/b", title="Example B", description=None),
    ]


@pytest.fixture
def sample_token_usage() -> TokenUsage:
    return TokenUsage(input_tokens=500, output_tokens=800, total_tokens=1300)


@pytest.fixture
def sample_agent_response(sample_sources: list[Source], sample_token_usage: TokenUsage) -> AgentResponse:
    return AgentResponse(
        response_text="# Research Response\n\nQuantum computing uses qubits...",
        sources=sample_sources,
        token_usage=sample_token_usage,
        tool_calls=[
            ToolCallRecord(tool_name="tavily_search", input_summary="quantum computing", success=True, latency_ms=250)
        ],
        is_complete=True,
    )


@pytest.fixture
def mock_agent(sample_agent_response: AgentResponse) -> MagicMock:
    agent = MagicMock()
    agent.stream.return_value = sample_agent_response
    return agent


@pytest.fixture
def mock_output_manager(tmp_output_dir: Path) -> MagicMock:
    manager = MagicMock()
    manager.write.return_value = tmp_output_dir / "test-query_20260525_120000.md"
    return manager
