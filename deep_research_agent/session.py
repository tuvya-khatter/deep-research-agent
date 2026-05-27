"""SessionManager — session lifecycle and per-query correlation ID tracking."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class QueryRecord:
    query_id: str
    query_text: str
    submitted_at: datetime


@dataclass
class Session:
    session_id: str
    start_time: datetime
    end_time: datetime | None = None
    queries: list[QueryRecord] = field(default_factory=list)


class SessionManager:
    """Manages session lifecycle and per-query correlation IDs."""

    def start_session(self) -> Session:
        return Session(
            session_id=str(uuid.uuid4()),
            start_time=datetime.now(tz=timezone.utc),
        )

    def end_session(self, session: Session) -> Session:
        session.end_time = datetime.now(tz=timezone.utc)
        return session

    def add_query(self, session: Session, query: str) -> QueryRecord:
        record = QueryRecord(
            query_id=str(uuid.uuid4()),
            query_text=query,
            submitted_at=datetime.now(tz=timezone.utc),
        )
        session.queries.append(record)
        return record

    def to_context_dict(self, session: Session, query: QueryRecord) -> dict[str, str]:
        return {
            "session_id": session.session_id,
            "query_id": query.query_id,
        }
