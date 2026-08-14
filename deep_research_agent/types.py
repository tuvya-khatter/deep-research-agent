"""Shared data classes for the Deep Research Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class ToolCallRecord:
    tool_name: str
    input_summary: str
    success: bool
    latency_ms: int


@dataclass
class Source:
    url: str
    title: str
    description: str | None = None


@dataclass
class SearchItem:
    url: str
    title: str
    snippet: str
    score: float


@dataclass
class ExtractionItem:
    url: str
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class CrawledPage:
    url: str
    content: str
    depth: int


@dataclass
class SearchResult:
    results: list[SearchItem]


@dataclass
class ExtractResult:
    extractions: list[ExtractionItem]


@dataclass
class CrawlResult:
    pages: list[CrawledPage]


@dataclass
class AgentResponse:
    response_text: str
    sources: list[Source]
    token_usage: TokenUsage
    tool_calls: list[ToolCallRecord]
    is_complete: bool = True


@dataclass
class OutputMetadata:
    query: str
    model_id: str
    session_id: str
    query_id: str
    generated_at: datetime
    source_count: int
    token_usage: TokenUsage | None = None


@dataclass
class ResearchResult:
    query: str
    response_text: str
    output_path: Path
    sources: list[Source]
    token_usage: TokenUsage
    duration_seconds: float
    session_id: str
    query_id: str
    is_complete: bool = True
