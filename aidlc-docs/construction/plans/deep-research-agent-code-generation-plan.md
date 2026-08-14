# Code Generation Plan — Deep Research Agent

## Unit: Deep Research Agent (Single Unit)
**Project Type**: Greenfield  
**Language**: Python 3.12+  
**Package Manager**: uv  
**Workspace Root**: `/Users/tuvyakhatter/Downloads/aidlc-rules/deep-research-agent/`

---

## Unit Context

### Stories Covered (all 13)
| Story | Title |
|---|---|
| US-001 | Configure Agent Credentials |
| US-002 | Start Interactive Research Session |
| US-003 | Submit Query with Streaming Output |
| US-004 | Run Multiple Queries in One Session |
| US-005 | Exit Session Cleanly |
| US-006 | Receive Research as Markdown File |
| US-007 | Verify Research Sources and Metadata |
| US-008 | Handle Missing or Invalid Credentials |
| US-009 | Handle Tavily API Failure |
| US-010 | Handle Bedrock Invocation Failure |
| US-011 | Handle Invalid or Empty Query |
| US-012 | Handle Interrupted Session |
| US-013 | Access Research Log File |

### Dependencies
- Amazon Bedrock (via Strands Agents SDK + boto3)
- Tavily APIs (search, extract, crawl)
- Strands Agents SDK
- Hypothesis (PBT framework — PBT-09)

### Code Location Rules
- **Application code**: `deep_research_agent/` and `tests/` in workspace root
- **Config/build files**: workspace root
- **Documentation summaries**: `aidlc-docs/construction/deep-research-agent/code/`

---

## Testable Properties (PBT-01 — advisory in partial mode)

| Component | Property Category | Property |
|---|---|---|
| `_sanitize_slug()` | Invariant | Output len ≤ 50; chars in `[a-z0-9-]`; no leading/trailing hyphens |
| `_sanitize_slug()` | Idempotence | `sanitize(sanitize(x)) == sanitize(x)` |
| `_format_markdown()` | Invariant | All required sections always present; source_count == len(sources) |
| `SessionManager.add_query()` | Invariant | `len(session.queries)` increases by exactly 1 per call |
| `SessionManager` IDs | Invariant | session_id and query_id always valid UUID4 strings |
| `CLI._validate_query()` | Invariant | Valid inputs never raise; empty/all-caps-single-word always raise |
| `TavilyExtractTool.execute()` | Invariant | Partial results: successful extractions ≥ 0; failed URLs not in result |
| `ResearchPipeline.run()` | Invariant | `result.duration_seconds` always ≥ 0 |

**PBT-02 (Round-trip)**: N/A — no serialization/deserialization or encoding/decoding pairs in this system. All transformations are lossy or one-way (slug sanitization is lossy; Markdown formatting is one-way; no parse/format inverses exist).

**Framework**: Hypothesis (Python) — satisfies PBT-09 (custom generators, automatic shrinking, seed reproducibility, pytest integration).

---

## Generation Steps

### Step 1 — Project Structure Setup
**Files**:
- `pyproject.toml`
- `.gitignore`
- `deep_research_agent/__init__.py`
- `deep_research_agent/tools/__init__.py`
- `tests/__init__.py`
- `README.md`

**pyproject.toml covers**:
- `[project]`: name, version, Python 3.12+, dependencies
- Dependencies: `strands-agents`, `boto3`, `tavily-python`, `hypothesis`
- Dev dependencies: `pytest`, `pytest-cov`, `ruff`, `mypy`
- `[project.scripts]`: entry point `deep-research-agent = "deep_research_agent.__main__:main"`
- `[tool.pytest.ini_options]`: testpaths, markers for `pbt`
- `[tool.ruff]`, `[tool.mypy]` baseline configs

**Stories**: Foundation for all  
- [x] Step 1 complete

---

### Step 2 — Shared Types (`deep_research_agent/types.py`)
**Contents**:
- `TokenUsage` dataclass (input_tokens, output_tokens, total_tokens)
- `ToolCallRecord` dataclass (tool_name, input_summary, success, latency_ms)
- `Source` dataclass (url, title, description: str | None)
- `SearchItem` dataclass (url, title, snippet, score)
- `ExtractionItem` dataclass (url, content, metadata: dict[str, str])
- `CrawledPage` dataclass (url, content, depth)
- `AgentResponse` dataclass (response_text, sources, token_usage, tool_calls, is_complete: bool)
- `OutputMetadata` dataclass (query, model_id, session_id, query_id, generated_at, source_count)
- `ResearchResult` dataclass (query, response_text, output_path, sources, token_usage, duration_seconds, session_id, query_id, is_complete)

**Stories**: Foundation  
- [x] Step 2 complete

---

### Step 3 — Custom Exceptions (`deep_research_agent/exceptions.py`)
**Contents**: Full hierarchy:
```
ResearchAgentError
├── ConfigurationError
├── BedrockError
├── TavilyError
│   ├── TavilySearchError
│   ├── TavilyExtractError
│   └── TavilyCrawlError
└── OutputError
```
Each exception: `__init__(self, message: str)`, stores message, no internal detail exposed.

**Stories**: US-008, US-009, US-010  
- [x] Step \1 complete

---

### Step 4 — Logging Setup (`deep_research_agent/logging_config.py`)
**Contents**: `setup_logging(log_dir: Path, console_level: str = "INFO", file_level: str = "DEBUG") -> None`
- `RotatingFileHandler`: `{log_dir}/deep_research_agent.log`, maxBytes=10_485_760, backupCount=5, encoding="utf-8"
- `StreamHandler`: console at `console_level`
- Root logger configured once; idempotent on repeated calls (guard with handler check)
- [SECURITY-03] No credentials or PII in format string

**Stories**: US-013  
- [x] Step \1 complete

---

### Step 5 — Tool Layer (`deep_research_agent/tools/tavily_tools.py`)
**Contents**:
- `SearchInput` dataclass (query: str, max_results: int = 10)
- `SearchResult` dataclass (results: list[SearchItem])
- `ExtractInput` dataclass (urls: list[str])
- `ExtractResult` dataclass (extractions: list[ExtractionItem])
- `CrawlInput` dataclass (url: str, max_depth: int = 2)
- `CrawlResult` dataclass (pages: list[CrawledPage])
- `BaseTavilyTool(ABC)`: `__init__(api_key: str)`, abstract `execute()`, abstract `as_strands_tool()`
- `TavilySearchTool(BaseTavilyTool)`:
  - Stores `max_results` as instance default
  - `execute(SearchInput) -> SearchResult`; raises `TavilySearchError`
  - `as_strands_tool()` → Strands `@tool`-decorated function wrapping `execute()`
- `TavilyExtractTool(BaseTavilyTool)`:
  - `execute(ExtractInput) -> ExtractResult`; per-URL retry-once (RULE-TAVILY-02)
  - Raises `TavilyExtractError` only if ALL URLs fail
  - `as_strands_tool()` → Strands `@tool`-decorated function
- `TavilyCrawlTool(BaseTavilyTool)`:
  - Stores `max_depth` as instance default
  - `execute(CrawlInput) -> CrawlResult`; raises `TavilyCrawlError`
  - `as_strands_tool()` → Strands `@tool`-decorated function
- [SECURITY-12] `api_key` stored only as instance variable, never logged

**Stories**: US-003, US-009  
- [x] Step \1 complete

---

### Step 6 — Output Manager (`deep_research_agent/output.py`)
**Contents**:
- `OutputManager` class with all methods:
  - `write(response_text, query, sources, metadata, output_dir) -> Path`
  - `_sanitize_slug(query: str) -> str` (RULE-OUT-02: lowercase, hyphens, max 50)
  - `_build_filename(slug: str, timestamp: datetime) -> str` (RULE-OUT-03)
  - `_resolve_filename(output_dir, slug, timestamp) -> Path` (RULE-OUT-04: collision counter)
  - `_format_markdown(response_text, sources, metadata) -> str` (RULE-OUT-01: all 8 sections)
  - `_ensure_output_dir(output_dir: Path) -> None` (RULE-OUT-05)
- Markdown template with all required sections (Q9=C: title, metadata table, response body, sources)

**Stories**: US-006, US-007  
- [x] Step \1 complete

---

### Step 7 — Research Agent (`deep_research_agent/agent.py`)
**Contents**:
- `ResearchAgent` class:
  - `__init__(model_id: str, tools: list[BaseTavilyTool]) -> None`
    - Construct Strands `Agent` with Bedrock provider (model_id)
    - Register all tools via `tool.as_strands_tool()` at construction time
  - `stream(query, session_context, callback) -> AgentResponse`
    - Calls `_build_system_prompt(session_context)` [Q1=B, Q2=B, Q3=C]
    - Invokes Strands agent with system prompt + query
    - Forwards tokens to callback (line-buffer is handled in pipeline, not here — raw tokens forwarded)
    - Extracts sources from tool call results in Strands event stream
    - Translates SDK exceptions to `BedrockError`
    - Returns `AgentResponse(is_complete=True)`
  - `_build_system_prompt(session_context: dict[str, str]) -> str`
    - Assembles prompt with: date, session_id, query_id, tool descriptions, recommended sequence

**Stories**: US-003, US-010  
- [x] Step \1 complete

---

### Step 8 — Research Pipeline (`deep_research_agent/pipeline.py`)
**Contents**:
- `ResearchPipeline` class:
  - `__init__(agent, output_manager)` — stores model_id for OutputMetadata
  - `run(query, session_context, output_dir, stream_callback) -> ResearchResult`
    - Token accumulation + line-buffer wrapper around stream_callback (Q8=C)
    - `_invoke_agent()`: wraps `ResearchAgent.stream()` with partial-save logic (Q13=B, RULE-BEDROCK-01)
    - `_save_output()`: calls `OutputManager.write()`
    - `_log_result()`: structured INFO log with all fields from RULE-LOG-01
    - Error boundaries: catches `BedrockError`, `TavilyError`, `OutputError`, bare `Exception`; raises `ResearchAgentError` with generic message (RULE-ERR-03, SECURITY-09)
  - `_invoke_agent()`: token_buffer accumulation; partial AgentResponse on BedrockError mid-stream (RULE-BEDROCK-01)

**Stories**: US-003, US-004, US-009, US-010, US-012  
- [x] Step \1 complete

---

### Step 9 — Session Manager (`deep_research_agent/session.py`)
**Contents**:
- `Session` dataclass (session_id, start_time, end_time, queries)
- `QueryRecord` dataclass (query_id, query_text, submitted_at)
- `SessionManager` class:
  - `start_session() -> Session` — UUID4 session_id, datetime.utcnow()
  - `end_session(session) -> Session` — sets end_time
  - `add_query(session, query) -> QueryRecord` — UUID4 query_id, appends to session.queries
  - `to_context_dict(session, query_record) -> dict[str, str]` — keys: session_id, query_id

**Stories**: US-002, US-004  
- [x] Step \1 complete

---

### Step 10 — CLI (`deep_research_agent/cli.py`)
**Contents**:
- `CLI` class:
  - `__init__(pipeline, session_manager)`
  - `run(model_id, output_dir) -> None` — full REPL loop per business-logic-model.md Section 2
    - session lifecycle (start/end)
    - exit command detection (RULE-EXIT-01): `exit`, `quit`, `q` + EOFError + KeyboardInterrupt
    - `_validate_query()` call + ValueError display
    - pipeline.run() call + retry/skip flow (RULE-ERR-02)
  - `_get_query() -> str | None` — `input()` with EOFError catch
  - `_validate_query(query: str) -> str` — RULE-QV-01/02/03/04
  - `_display_stream(token: str) -> None` — line-buffer flush on `\n` (RULE-STREAM-01)
  - `_prompt_retry_or_skip() -> str` — returns `"retry"` or `"skip"`
  - `_display_error(err: ResearchAgentError) -> None` — generic message only (RULE-ERR-03)
  - `_display_separator() -> None`
  - `_display_output_path(path: Path) -> None`
  - `_flush_line_buffer() -> None` — flush remaining buffer on query complete

**Stories**: US-002, US-003, US-004, US-005, US-011, US-012  
- [x] Step \1 complete

---

### Step 11 — Entry Point (`deep_research_agent/__main__.py`)
**Contents**:
- `main() -> None` — startup orchestration per business-logic-model.md Section 1
- `_parse_args() -> argparse.Namespace`
  - `--model` (str, required: default model ID)
  - `--output-dir` (Path, default: `./research-output`)
  - `--max-search-results` (int, default: 10, min: 1, max: 50) [Q16]
  - `--max-crawl-depth` (int, default: 2, min: 1, max: 5) [Q16]
- `_validate_credentials() -> None`
  - Check `TAVILY_API_KEY` non-empty [US-001, US-008]
  - Check AWS credential chain via boto3 [US-001, US-008]
  - Raises `ConfigurationError` with actionable message; no credential values in messages (SECURITY-09, SECURITY-12)
- Component wiring in exact order from services.md Entry Point Composition

**Stories**: US-001, US-002, US-008  
- [x] Step \1 complete

---

### Step 12 — Test Infrastructure (`tests/conftest.py`)
**Contents**:
- `pytest` fixtures:
  - `tavily_api_key` — fixed test key string (never a real key)
  - `mock_agent_response` — factory fixture for `AgentResponse`
  - `mock_research_result` — factory fixture for `ResearchResult`
  - `tmp_output_dir` — `tmp_path`-backed output directory
  - `mock_session` / `mock_query_record` — pre-built Session/QueryRecord
- Hypothesis strategies (PBT-07 — domain generators):
  - `query_text()` — `st.text(min_size=1)` filtered for at least 1 alphanumeric char, not single all-caps word
  - `valid_slug_input()` — text strings with realistic query characters
  - `source_list()` — `st.lists(st.builds(Source, url=st.from_regex(...), title=st.text(min_size=1), description=st.one_of(st.none(), st.text())), max_size=10)`
  - `token_usage()` — `st.builds(TokenUsage, input_tokens=st.integers(min_value=0), ...)`
  - `session_context()` — `st.fixed_dictionaries({"session_id": st.uuids(), "query_id": st.uuids()})`
  - All strategies exported for reuse across test files (PBT-07 reusability)
- Hypothesis settings: `suppress_health_check=[]`, `deriving=True` (shrinking enabled, PBT-08)

**Stories**: Foundation for all tests  
- [x] Step \1 complete

---

### Step 13 — Unit Tests: Tool Layer (`tests/test_tools.py`)
**Contents** (example-based):
- `TavilySearchTool`: success path, `TavilySearchError` on HTTP failure, uses `max_results` instance default
- `TavilyExtractTool`: success path, per-URL retry-once (first attempt fails, second succeeds), all-URLs-fail raises `TavilyExtractError`, partial result when some URLs succeed
- `TavilyCrawlTool`: success path, `TavilyCrawlError` on failure
- `BaseTavilyTool`: abstractness enforced (cannot instantiate)
- Strands tool registration: `as_strands_tool()` returns callable

**Stories**: US-009  
- [x] Step \1 complete

---

### Step 14 — Unit Tests: Output Manager (`tests/test_output.py`)
**Contents** (example-based):
- `_sanitize_slug`: spaces→hyphens, special chars stripped, max 50, empty fallback to "research", all-non-alpha falls back
- `_build_filename`: correct format `{slug}_{YYYYMMDD_HHMMSS}.md`
- `_resolve_filename`: no collision returns base, collision appends `_1`, `_2`, etc.
- `_format_markdown`: all 8 sections present, source URLs in output, metadata fields correct, incomplete marker preserved
- `_ensure_output_dir`: creates dir, raises `OutputError` on permission failure
- `write()`: end-to-end, returns valid Path, file exists with expected content

**PBT (in this file, named `test_property_*`)** — PBT-03, PBT-07, PBT-08:
- `test_property_sanitize_slug_length`: for all valid query strings, `len(_sanitize_slug(q)) <= 50`
- `test_property_sanitize_slug_charset`: for all valid query strings, slug matches `^[a-z0-9][a-z0-9-]*[a-z0-9]$` or is single-char `[a-z0-9]` or `"research"`
- `test_property_sanitize_slug_idempotent`: `_sanitize_slug(_sanitize_slug(q)) == _sanitize_slug(q)`
- `test_property_format_markdown_sections`: for all valid (response_text, sources, metadata) combos, all 8 section markers always present in output
- `test_property_format_markdown_source_count`: `metadata.source_count == len(sources)` always reflected correctly

**Stories**: US-006, US-007  
- [x] Step \1 complete

---

### Step 15 — Unit Tests: Research Agent (`tests/test_agent.py`)
**Contents** (example-based):
- `_build_system_prompt`: contains date, session_id, query_id, tool names, recommended sequence keywords; no API keys in prompt (SECURITY-12)
- `stream()`: mocked Strands SDK — success path returns `AgentResponse(is_complete=True)`, SDK exception raises `BedrockError`
- Tool registration: all 3 tools registered at construction time

**Stories**: US-003, US-010  
- [x] Step \1 complete

---

### Step 16 — Unit Tests: Research Pipeline (`tests/test_pipeline.py`)
**Contents** (example-based):
- `run()` success: stream_callback called with tokens; `ResearchResult` fields correct; output file written; log entry made
- `run()` + `BedrockError` with tokens: partial `AgentResponse` returned; output file written with `[INCOMPLETE]` marker
- `run()` + `BedrockError` without tokens: `ResearchAgentError` raised; no output file
- `run()` + `TavilyError`: `ResearchAgentError` raised with generic message
- `run()` + `OutputError`: `ResearchAgentError` raised
- `_log_result()`: all RULE-LOG-01 fields present in log output; no credentials logged
- Line-buffer: tokens accumulated correctly; newline triggers flush

**PBT (in this file, named `test_property_*`)** — PBT-03, PBT-07, PBT-08:
- `test_property_result_duration_non_negative`: for all valid run configurations, `result.duration_seconds >= 0`

**Stories**: US-003, US-004, US-009, US-010, US-012  
- [x] Step \1 complete

---

### Step 17 — Unit Tests: Session Manager (`tests/test_session.py`)
**Contents** (example-based):
- `start_session()`: valid Session returned, session_id is UUID4, queries empty
- `end_session()`: end_time set, session_id unchanged
- `add_query()`: QueryRecord appended, query_id is UUID4, query_text preserved
- `to_context_dict()`: returns dict with exactly keys `session_id`, `query_id` as strings

**PBT (in this file, named `test_property_*`)** — PBT-03, PBT-07, PBT-08:
- `test_property_add_query_increments_count`: for any n calls to `add_query`, `len(session.queries) == n`
- `test_property_session_id_is_uuid4`: for all generated sessions, `session_id` matches UUID4 pattern
- `test_property_context_dict_keys`: for all (session, query_record) pairs, `to_context_dict` returns dict with exactly `{"session_id", "query_id"}` keys

**Stories**: US-002, US-004  
- [x] Step \1 complete

---

### Step 18 — Unit Tests: CLI (`tests/test_cli.py`)
**Contents** (example-based):
- `_validate_query()`: empty string raises `ValueError`; whitespace-only raises `ValueError`; single-word all-caps raises `ValueError`; normal query returns stripped string
- `_get_query()`: EOF returns None; keyboard text returns string
- Exit detection: `exit`, `quit`, `q` (case-insensitive) trigger loop break; other strings proceed to validate
- `_prompt_retry_or_skip()`: `r`/`retry` returns `"retry"`; `s`/`skip`/other returns `"skip"`
- `_display_stream()`: line buffer accumulates; flushes on `\n`; `_flush_line_buffer()` clears remainder
- `run()` happy path (mocked pipeline): full REPL loop processes one query and exits cleanly
- `run()` error path: `ResearchAgentError` triggers retry prompt; retry re-runs pipeline; skip returns to prompt

**PBT (in this file, named `test_property_*`)** — PBT-03, PBT-07, PBT-08:
- `test_property_validate_query_valid_inputs_never_raise`: for all generated valid query texts (at least 1 alphanumeric, not single all-caps), `_validate_query()` never raises
- `test_property_validate_query_empty_always_raises`: for all whitespace-only strings, `_validate_query()` always raises `ValueError`

**Stories**: US-002, US-003, US-004, US-005, US-011, US-012  
- [x] Step \1 complete

---

### Step 19 — Code Summary Documentation
**Files**:
- `aidlc-docs/construction/deep-research-agent/code/code-summary.md`

**Contents**:
- File manifest with paths and responsibilities
- Story traceability matrix (story → files)
- PBT compliance summary (which files contain `test_property_*` tests and what properties they cover)
- Extension compliance notes (SECURITY, PBT)

**Stories**: N/A (documentation)  
- [x] Step \1 complete

---

## Extension Compliance — Planning Stage

### Security Baseline
| Rule | Status at Planning |
|---|---|
| SECURITY-03 | Plan includes `logging_config.py` (Step 4) with no-credentials constraint |
| SECURITY-05 | Plan includes `_validate_query()` (Step 10) and `_parse_args()` (Step 11) validation |
| SECURITY-09 | Plan includes generic error messages in `CLI._display_error()` and `ResearchPipeline` error boundaries |
| SECURITY-11 | Plan isolates credential logic in `__main__._validate_credentials()` only |
| SECURITY-12 | Plan includes no-credentials-in-logs and no-credentials-in-prompts constraints in Steps 4, 7, 11 |
| SECURITY-15 | Plan includes global try/except in `CLI.run()` and per-external-call error handlers in pipeline, tools |

### PBT Extension (Partial: PBT-02, PBT-03, PBT-07, PBT-08, PBT-09)
| Rule | Status |
|---|---|
| PBT-02 (Round-trip) | N/A — no serialization/deserialization pairs in this system |
| PBT-03 (Invariant) | Compliant — plan includes invariant PBT tests in Steps 14, 16, 17, 18 |
| PBT-07 (Generator Quality) | Compliant — domain-specific Hypothesis strategies defined in Step 12 conftest.py |
| PBT-08 (Shrinking/Reproducibility) | Compliant — Hypothesis used (shrinking built-in); seed logged on failure by default |
| PBT-09 (Framework Selection) | Compliant — `hypothesis` added to pyproject.toml in Step 1; `pytest-hypothesis` integration |
