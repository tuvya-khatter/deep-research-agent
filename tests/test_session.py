"""Unit tests and property-based tests for SessionManager.

PBT invariants (PBT-03, PBT-07, PBT-08):
- test_property_add_query_increments_count
- test_property_session_id_is_uuid4
- test_property_context_dict_keys
"""

from __future__ import annotations

import re
import uuid

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.conftest import query_text

from deep_research_agent.session import QueryRecord, Session, SessionManager

_UUID4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager()


class TestStartSession:
    def test_returns_session(self, manager: SessionManager) -> None:
        session = manager.start_session()
        assert isinstance(session, Session)

    def test_session_id_is_uuid4(self, manager: SessionManager) -> None:
        session = manager.start_session()
        assert _UUID4_PATTERN.match(session.session_id)

    def test_queries_empty_on_start(self, manager: SessionManager) -> None:
        session = manager.start_session()
        assert session.queries == []

    def test_end_time_none_on_start(self, manager: SessionManager) -> None:
        session = manager.start_session()
        assert session.end_time is None


class TestEndSession:
    def test_sets_end_time(self, manager: SessionManager) -> None:
        session = manager.start_session()
        ended = manager.end_session(session)
        assert ended.end_time is not None

    def test_session_id_unchanged(self, manager: SessionManager) -> None:
        session = manager.start_session()
        original_id = session.session_id
        manager.end_session(session)
        assert session.session_id == original_id


class TestAddQuery:
    def test_returns_query_record(self, manager: SessionManager) -> None:
        session = manager.start_session()
        record = manager.add_query(session, "What is AI?")
        assert isinstance(record, QueryRecord)

    def test_query_id_is_uuid4(self, manager: SessionManager) -> None:
        session = manager.start_session()
        record = manager.add_query(session, "test query")
        assert _UUID4_PATTERN.match(record.query_id)

    def test_query_text_preserved(self, manager: SessionManager) -> None:
        session = manager.start_session()
        record = manager.add_query(session, "exact text")
        assert record.query_text == "exact text"

    def test_appended_to_session_queries(self, manager: SessionManager) -> None:
        session = manager.start_session()
        manager.add_query(session, "q1")
        manager.add_query(session, "q2")
        assert len(session.queries) == 2

    def test_each_query_has_unique_id(self, manager: SessionManager) -> None:
        session = manager.start_session()
        r1 = manager.add_query(session, "q1")
        r2 = manager.add_query(session, "q2")
        assert r1.query_id != r2.query_id


class TestToContextDict:
    def test_returns_dict_with_correct_keys(self, manager: SessionManager) -> None:
        session = manager.start_session()
        record = manager.add_query(session, "query")
        ctx = manager.to_context_dict(session, record)
        assert set(ctx.keys()) == {"session_id", "query_id"}

    def test_values_match_ids(self, manager: SessionManager) -> None:
        session = manager.start_session()
        record = manager.add_query(session, "query")
        ctx = manager.to_context_dict(session, record)
        assert ctx["session_id"] == session.session_id
        assert ctx["query_id"] == record.query_id

    def test_values_are_strings(self, manager: SessionManager) -> None:
        session = manager.start_session()
        record = manager.add_query(session, "query")
        ctx = manager.to_context_dict(session, record)
        assert all(isinstance(v, str) for v in ctx.values())


# ---------------------------------------------------------------------------
# Property-Based Tests (PBT-03, PBT-07, PBT-08)
# ---------------------------------------------------------------------------

@pytest.mark.pbt
@given(queries=st.lists(query_text(), min_size=0, max_size=20))
def test_property_add_query_increments_count(queries: list[str]) -> None:
    """Invariant: len(session.queries) == number of add_query calls."""
    manager = SessionManager()
    session = manager.start_session()
    for i, q in enumerate(queries):
        manager.add_query(session, q)
        assert len(session.queries) == i + 1


@pytest.mark.pbt
@given(n=st.integers(min_value=1, max_value=10))
def test_property_session_id_is_uuid4(n: int) -> None:
    """Invariant: every session_id is a valid UUID4 string."""
    manager = SessionManager()
    for _ in range(n):
        session = manager.start_session()
        assert _UUID4_PATTERN.match(session.session_id), (
            f"Invalid UUID4: {session.session_id}"
        )


@pytest.mark.pbt
@given(query=query_text())
def test_property_context_dict_keys(query: str) -> None:
    """Invariant: to_context_dict always returns exactly {session_id, query_id}."""
    manager = SessionManager()
    session = manager.start_session()
    record = manager.add_query(session, query)
    ctx = manager.to_context_dict(session, record)
    assert set(ctx.keys()) == {"session_id", "query_id"}
    assert all(isinstance(v, str) for v in ctx.values())
