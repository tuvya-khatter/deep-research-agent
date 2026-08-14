# Components

## Architectural Pattern: Layered

```
+---------------------------+
|       CLI LAYER           |
|  CLI   |  SessionManager  |
+---------------------------+
|   SERVICE / ORCH LAYER    |
|  ResearchPipeline         |
|  ResearchAgent            |
+---------------------------+
|  TOOL / INTEGRATION LAYER |
|  TavilyTools              |
|  (Search, Extract, Crawl) |
+---------------------------+
|   INFRASTRUCTURE LAYER    |
|  OutputManager            |
|  LoggerSetup              |
+---------------------------+
```

Configuration (credentials, model ID, output dir) is loaded inline in `__main__.py` — no dedicated config component.

---

## Component 1: CLI

**Module**: `deep_research_agent/cli.py`  
**Layer**: CLI

**Responsibilities**:
- Parse CLI arguments (`--model`, `--output-dir`)
- Run the interactive REPL loop
- Display streaming LLM tokens to stdout as they arrive
- Prompt the user for research queries
- Validate that queries are non-empty before passing to the pipeline
- Handle exit commands (`exit`, `quit`) and `Ctrl+C` gracefully
- Display visual separators between query sessions

**Interfaces**:
- Accepts: `ResearchPipeline`, `SessionManager` instances at construction
- Emits: streaming tokens to stdout; calls `pipeline.run()` per query

---

## Component 2: SessionManager

**Module**: `deep_research_agent/session.py`  
**Layer**: CLI

**Responsibilities**:
- Generate unique session and query correlation IDs (UUID4)
- Track session start/end timestamps
- Maintain an ordered list of queries submitted within a session
- Provide session context dictionaries consumed by the pipeline and logger

**Interfaces**:
- Accepts: no external dependencies
- Emits: `Session` and `QueryRecord` data objects

---

## Component 3: ResearchPipeline

**Module**: `deep_research_agent/pipeline.py`  
**Layer**: Service / Orchestration

**Responsibilities**:
- Own the end-to-end research flow for a single query:
  1. Invoke `ResearchAgent` with streaming callback
  2. Collect the completed response and source metadata
  3. Invoke `OutputManager` to write the Markdown file
  4. Log token usage, latency, and source count via the module logger
- Return a `ResearchResult` to the CLI (file path, summary, timing)
- Catch and handle `TavilyError` and `BedrockError` — surface user-friendly messages; never crash the session

**Interfaces**:
- Accepts: `ResearchAgent`, `OutputManager` instances at construction
- Emits: `ResearchResult`; streaming tokens forwarded to CLI via callback

---

## Component 4: ResearchAgent

**Module**: `deep_research_agent/agent.py`  
**Layer**: Service / Orchestration

**Responsibilities**:
- Wrap the Strands Agents SDK `Agent` class
- Configure the Bedrock LLM provider with the selected model ID
- Register all three `TavilyTool` instances as Strands tools at construction
- Attach session context (correlation ID, query ID) to each invocation
- Expose a streaming interface that forwards tokens via a callback
- Return `AgentResponse` containing the full response text and any metadata Strands provides (token counts, tool calls made)

**Interfaces**:
- Accepts: `model_id: str`, `tools: list[BaseTavilyTool]` at construction
- Emits: `AgentResponse`; streaming tokens via provided callback

---

## Component 5: TavilyTools

**Module**: `deep_research_agent/tools/`  
**Layer**: Tool / Integration

**Sub-components** (all in `deep_research_agent/tools/tavily_tools.py`):
- `BaseTavilyTool` — abstract base class defining the shared interface and error handling contract
- `TavilySearchTool` — Tavily Search API integration
- `TavilyExtractTool` — Tavily Extract API integration
- `TavilyCrawlTool` — Tavily Crawl API integration

**Responsibilities** (shared):
- Implement the `BaseTavilyTool` interface
- Execute the respective Tavily API call
- Parse and return typed results
- Raise `TavilyError` subclasses on API failure
- Expose each tool as a Strands-registered tool callable

**Interfaces**:
- Accepts: `api_key: str` at construction (loaded from env at startup, injected)
- Emits: `SearchResult`, `ExtractResult`, `CrawlResult` respectively

---

## Component 6: OutputManager

**Module**: `deep_research_agent/output.py`  
**Layer**: Infrastructure

**Responsibilities**:
- Assemble the Markdown research document from response text, sources, and metadata
- Sanitize the query string into a valid filename slug
- Generate a timestamped filename following the pattern `{slug}_{YYYYMMDD_HHMMSS}.md`
- Create the output directory if it does not exist
- Write the Markdown file atomically
- Raise `OutputError` on write failure

**Interfaces**:
- Accepts: response text, query string, source list, metadata, output directory path
- Emits: `Path` to the written file

---

## Component 7: LoggerSetup

**Module**: `deep_research_agent/logging_config.py`  
**Layer**: Infrastructure

**Responsibilities**:
- Configure the root Python logger at application startup
- Attach a `RotatingFileHandler` writing to `logs/research-agent.log`
- Attach a `StreamHandler` (stdout) at INFO level for console output
- Apply a structured log formatter (ISO 8601 timestamp, level, correlation ID, message)
- All other modules obtain loggers via `logging.getLogger(__name__)` — no further setup needed in those modules

**Interfaces**:
- Exports: `setup_logging(log_dir: Path, log_level: str) -> None`
- All components consume via stdlib `logging.getLogger(__name__)`

---

## Exception Hierarchy

**Module**: `deep_research_agent/exceptions.py`

```
ResearchAgentError          (base — all application errors)
├── ConfigurationError      (missing credentials, invalid CLI args)
├── BedrockError            (LLM invocation failures)
├── TavilyError             (base for all Tavily failures)
│   ├── TavilySearchError
│   ├── TavilyExtractError
│   └── TavilyCrawlError
└── OutputError             (file write failures)
```
