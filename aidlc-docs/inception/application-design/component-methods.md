# Component Methods

High-level method signatures for each component. Detailed business logic and rules are defined in Functional Design (Construction phase).

---

## CLI (`deep_research_agent/cli.py`)

```python
class CLI:
    def __init__(
        self,
        pipeline: ResearchPipeline,
        session_manager: SessionManager,
    ) -> None: ...

    def run(self, model_id: str, output_dir: Path) -> None:
        """Start the REPL loop. Blocks until user exits."""

    def _get_query(self) -> str | None:
        """Prompt user for input. Returns None on exit command or EOF."""

    def _validate_query(self, query: str) -> str:
        """Strip whitespace, enforce non-empty, enforce max length.
        Raises ValueError with user-friendly message on invalid input."""

    def _display_stream(self, token: str) -> None:
        """Write a single streamed token to stdout (no newline flush)."""

    def _display_separator(self) -> None:
        """Print visual separator line between query results."""

    def _display_output_path(self, path: Path) -> None:
        """Inform user where the output file was written."""
```

---

## SessionManager (`deep_research_agent/session.py`)

```python
@dataclass
class Session:
    session_id: str          # UUID4
    start_time: datetime
    end_time: datetime | None
    queries: list[QueryRecord]

@dataclass
class QueryRecord:
    query_id: str            # UUID4
    query_text: str
    submitted_at: datetime

class SessionManager:
    def start_session(self) -> Session:
        """Create and return a new Session with a fresh correlation ID."""

    def end_session(self, session: Session) -> Session:
        """Mark session end_time and return the completed Session."""

    def add_query(self, session: Session, query: str) -> QueryRecord:
        """Append a new QueryRecord to session.queries and return it."""

    def to_context_dict(self, session: Session, query: QueryRecord) -> dict[str, str]:
        """Return a flat dict of session/query IDs for log and agent context."""
```

---

## ResearchPipeline (`deep_research_agent/pipeline.py`)

```python
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

class ResearchPipeline:
    def __init__(
        self,
        agent: ResearchAgent,
        output_manager: OutputManager,
    ) -> None: ...

    def run(
        self,
        query: str,
        session_context: dict[str, str],
        output_dir: Path,
        stream_callback: Callable[[str], None],
    ) -> ResearchResult:
        """Run the full research pipeline for one query.
        Streams tokens via stream_callback.
        Writes output file. Returns ResearchResult."""

    def _invoke_agent(
        self,
        query: str,
        session_context: dict[str, str],
        stream_callback: Callable[[str], None],
    ) -> AgentResponse:
        """Call ResearchAgent.stream(); surface BedrockError on failure."""

    def _save_output(
        self,
        response: AgentResponse,
        query: str,
        output_dir: Path,
        session_context: dict[str, str],
    ) -> Path:
        """Call OutputManager.write(); surface OutputError on failure."""

    def _log_result(self, result: ResearchResult) -> None:
        """Log token counts, latency, source count, and file path."""
```

---

## ResearchAgent (`deep_research_agent/agent.py`)

```python
@dataclass
class AgentResponse:
    response_text: str
    sources: list[Source]
    token_usage: TokenUsage    # input_tokens, output_tokens
    tool_calls: list[ToolCallRecord]

class ResearchAgent:
    def __init__(
        self,
        model_id: str,
        tools: list[BaseTavilyTool],
    ) -> None:
        """Construct Strands Agent with Bedrock provider and registered tools."""

    def stream(
        self,
        query: str,
        session_context: dict[str, str],
        callback: Callable[[str], None],
    ) -> AgentResponse:
        """Invoke the Strands agent. Forward tokens via callback.
        Return full AgentResponse on completion.
        Raises BedrockError on LLM failure."""
```

---

## BaseTavilyTool (`deep_research_agent/tools/tavily_tools.py`)

```python
class BaseTavilyTool(ABC):
    def __init__(self, api_key: str) -> None: ...

    @abstractmethod
    def execute(self, input: ToolInput) -> ToolResult:
        """Execute the Tavily API call. Raises TavilyError subclass on failure."""

    @abstractmethod
    def as_strands_tool(self) -> Any:
        """Return the Strands tool registration object for this tool."""
```

## TavilySearchTool

```python
@dataclass
class SearchInput:
    query: str
    max_results: int = 10

@dataclass
class SearchResult:
    results: list[SearchItem]   # url, title, snippet, score

class TavilySearchTool(BaseTavilyTool):
    def execute(self, input: SearchInput) -> SearchResult:
        """Call Tavily Search API. Raises TavilySearchError on failure."""

    def as_strands_tool(self) -> Any: ...
```

## TavilyExtractTool

```python
@dataclass
class ExtractInput:
    urls: list[str]

@dataclass
class ExtractResult:
    extractions: list[ExtractionItem]   # url, content, metadata

class TavilyExtractTool(BaseTavilyTool):
    def execute(self, input: ExtractInput) -> ExtractResult:
        """Call Tavily Extract API. Raises TavilyExtractError on failure."""

    def as_strands_tool(self) -> Any: ...
```

## TavilyCrawlTool

```python
@dataclass
class CrawlInput:
    url: str
    max_depth: int = 2

@dataclass
class CrawlResult:
    pages: list[CrawledPage]   # url, content, depth

class TavilyCrawlTool(BaseTavilyTool):
    def execute(self, input: CrawlInput) -> CrawlResult:
        """Call Tavily Crawl API. Raises TavilyCrawlError on failure."""

    def as_strands_tool(self) -> Any: ...
```

---

## OutputManager (`deep_research_agent/output.py`)

```python
@dataclass
class Source:
    url: str
    title: str
    description: str | None

@dataclass
class OutputMetadata:
    query: str
    model_id: str
    session_id: str
    query_id: str
    generated_at: datetime
    source_count: int

class OutputManager:
    def write(
        self,
        response_text: str,
        query: str,
        sources: list[Source],
        metadata: OutputMetadata,
        output_dir: Path,
    ) -> Path:
        """Generate and write the Markdown research file. Returns file path.
        Raises OutputError on write failure."""

    def _sanitize_slug(self, query: str) -> str:
        """Convert query to a safe, lowercase, hyphenated filename slug."""

    def _build_filename(self, slug: str, timestamp: datetime) -> str:
        """Return '{slug}_{YYYYMMDD_HHMMSS}.md'."""

    def _format_markdown(
        self,
        response_text: str,
        sources: list[Source],
        metadata: OutputMetadata,
    ) -> str:
        """Assemble the full Markdown document string."""

    def _ensure_output_dir(self, output_dir: Path) -> None:
        """Create output_dir if it does not exist. Raises OutputError on permission failure."""
```

---

## LoggerSetup (`deep_research_agent/logging_config.py`)

```python
def setup_logging(
    log_dir: Path,
    console_level: str = "INFO",
    file_level: str = "DEBUG",
) -> None:
    """Configure root logger with RotatingFileHandler and StreamHandler.
    Must be called once at application startup before any other imports log."""
```

---

## Entry Point (`deep_research_agent/__main__.py`)

```python
def main() -> None:
    """Parse args, validate credentials, setup logging,
    construct all components, run CLI."""

def _parse_args() -> argparse.Namespace:
    """Parse --model and --output-dir from sys.argv."""

def _validate_credentials() -> None:
    """Check TAVILY_API_KEY env var and AWS credential chain.
    Raises ConfigurationError with actionable message on failure."""
```

---

## Shared Data Types (`deep_research_agent/types.py`)

```python
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
```
