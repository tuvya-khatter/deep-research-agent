# Requirements Document

## Intent Analysis

- **User Request**: Build a deep research agent using Strands Agents SDK integrated with Amazon Bedrock (LLMs) and Tavily APIs (web search, crawl, extract). No UI — interactive CLI with streaming responses. Markdown output written to files.
- **Request Type**: New Project (Greenfield)
- **Scope Estimate**: Multiple Components — CLI interface, research orchestrator, Bedrock LLM integration, Tavily integration (search + extract + crawl), output management, logging
- **Complexity Estimate**: Moderate-to-Complex — multi-service agentic orchestration, streaming, tool use, verbose observability

---

## Functional Requirements

### FR-01: Interactive CLI Interface
- The agent MUST provide an interactive REPL-like CLI session
- On launch with no arguments, the agent enters a prompt loop where the user can submit multiple research queries sequentially
- Each query initiates a full research run; results are streamed to the terminal as they are generated
- The user can exit the session via a standard signal (e.g., `Ctrl+C`, `exit`, `quit`)
- The CLI MUST display real-time streaming output from the LLM during research and synthesis

### FR-02: Configurable Bedrock LLM
- The agent MUST support runtime configuration of the Amazon Bedrock model
- Model selection MUST be configurable via CLI argument (e.g., `--model`) and/or a config file
- Default model MUST be documented and sensible (e.g., Claude 3.5 Sonnet)
- Supported models: any Amazon Bedrock-hosted Claude model (Claude 3.5 Sonnet, Claude 3.7 Sonnet, Claude 3 Opus, etc.)
- Model ID MUST be passed through to the Strands Agents SDK at agent initialization

### FR-03: Tavily Full Integration (Search + Extract + Crawl)
- The agent MUST integrate all three Tavily API capabilities:
  - **Search**: Submit queries to Tavily Search API to retrieve ranked URLs and content snippets
  - **Extract**: Submit URLs to Tavily Extract API to retrieve full page text/content
  - **Crawl**: Use Tavily Crawl API to deep-crawl linked pages from seed URLs
- The agent MUST expose these as tools available to the Strands agent for autonomous use
- The agent autonomously decides which Tavily tools to invoke and how many sources to collect based on topic complexity

### FR-04: Agent-Driven Research Depth
- The research agent MUST autonomously determine how many sub-queries, sources, and extraction/crawl operations are needed
- No fixed upper limit imposed by the framework; the agent uses its own reasoning to assess completeness
- The agent MUST signal its research strategy to the user via the CLI (e.g., "Searching for X...", "Extracting content from Y sources...", "Crawling Z for deeper context...")

### FR-05: Research Output — Single Markdown File Per Query
- Each research query MUST produce exactly one Markdown output file
- The file MUST be written to a configurable output directory (default: `./research-output/`)
- File naming convention: `{sanitized-topic-slug}_{YYYYMMDD_HHMMSS}.md`
- The Markdown file MUST include:
  - Title (derived from the research query)
  - Executive summary
  - Detailed findings organized by topic/subtopic
  - Sources cited with URLs
  - Generation metadata (timestamp, model used, Tavily API calls made)

### FR-06: Credential Management
- **Amazon Bedrock**: MUST use the standard AWS credential chain (environment variables → shared credentials file → AWS profiles → instance metadata)
- **Tavily API**: MUST be loaded from the `TAVILY_API_KEY` environment variable
- No credentials MUST ever be hardcoded in source code
- The agent MUST fail fast with a clear error message if required credentials are missing at startup

### FR-07: Strands Agents SDK Integration
- The agent MUST be implemented using the Strands Agents SDK
- Tavily tools (search, extract, crawl) MUST be registered as Strands agent tools
- The Bedrock model MUST be configured as the agent's LLM provider via the Strands SDK
- Streaming output from the Strands agent MUST be rendered to the CLI in real time

---

## Non-Functional Requirements

### NFR-01: Streaming Response
- LLM output MUST be streamed token-by-token to the CLI; users MUST NOT wait for the full response before seeing output
- Tool invocation status (search, extract, crawl calls) MUST also be displayed as they occur

### NFR-02: Verbose Logging and Observability
- Structured logging MUST be written to a rotating log file (`logs/research-agent.log`)
- Log entries MUST include: ISO 8601 timestamp, log level, correlation ID per research session, message
- The following MUST be logged:
  - Every Tavily API call (endpoint, query/URL, response status, latency)
  - Every Bedrock/LLM invocation (model ID, prompt token count, completion token count, latency)
  - Every tool invocation and result summary
  - Session start/end with total token usage and wall-clock duration
- Sensitive data (API keys, personal data) MUST NOT appear in logs
- Log level MUST be configurable (default: DEBUG for file, INFO for console)

### NFR-03: Python 3.12+ with uv
- The project MUST use Python 3.12 or higher
- Dependency management MUST use `uv` (fast Python package manager)
- All dependencies MUST be pinned in a lock file (`uv.lock`) committed to version control
- A `pyproject.toml` MUST define project metadata, dependencies, and entry points

### NFR-04: Performance
- The CLI MUST remain responsive during research (streaming output prevents perceived blocking)
- Tavily API calls SHOULD be made concurrently where the agent deems independent queries parallelizable
- No artificial rate limiting imposed by the agent code unless Tavily API rate limits are encountered

### NFR-05: Error Handling and Resilience
- Network errors to Tavily APIs MUST be caught and handled gracefully (retry with backoff or skip with warning)
- Bedrock invocation errors MUST be caught with a clear user-facing error message
- The agent MUST NOT crash the CLI session on a single failed research query; the user MUST be able to submit another query

### NFR-06: Testability
- Core business logic (research orchestration, output formatting, tool wrappers) MUST be unit-testable in isolation
- Integration tests MUST cover Tavily tool invocations with mocked HTTP responses
- Tests MUST be runnable via a single command (`uv run pytest`)

---

## Extension Requirements

### Security (Full Enforcement)
All SECURITY-01 through SECURITY-15 rules apply. Key constraints for this project:

- **SECURITY-03**: Structured logging configured; no secrets or PII in logs
- **SECURITY-05**: CLI input (research queries) MUST be validated for length/type before passing to the agent
- **SECURITY-06**: AWS IAM role/policy for Bedrock access MUST use least-privilege (specific actions and resources only)
- **SECURITY-09**: No default credentials; production error responses MUST NOT expose stack traces to the user
- **SECURITY-10**: All dependencies pinned in `uv.lock`; vulnerability scanning included in build instructions
- **SECURITY-11**: Rate limiting considered for Tavily API calls; misuse scenarios documented
- **SECURITY-12**: No hardcoded credentials anywhere in source code or config files
- **SECURITY-15**: All external API calls (Bedrock, Tavily) MUST have explicit error handling; fail closed on unexpected errors

Rules SECURITY-01 (encryption at rest — no data store), SECURITY-02 (load balancer logging — no LB), SECURITY-04 (HTTP headers — no web app), SECURITY-07 (network config — no VPC), SECURITY-08 (app-level access control — no auth layer), SECURITY-13 (deserialization/CI), SECURITY-14 (alerting/retention) are evaluated per-stage.

### Property-Based Testing (Partial Enforcement)
Enforced rules: **PBT-02, PBT-03, PBT-07, PBT-08, PBT-09**. All others are advisory.

- **PBT-02**: Round-trip tests MUST be written for any serialization/deserialization (e.g., research output Markdown formatting, config parsing)
- **PBT-03**: Invariant tests MUST be written for data transformation functions (e.g., topic slug sanitization, source deduplication)
- **PBT-07**: Domain-specific generators MUST be used (e.g., valid research queries, URL lists, Tavily response payloads)
- **PBT-08**: Hypothesis framework shrinking MUST be enabled; seed logged on failure; PBT included in CI
- **PBT-09**: **Hypothesis** selected as the PBT framework (Python 3.12, integrates with pytest)

---

## Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Agent Framework | Strands Agents SDK | User specified |
| LLM Provider | Amazon Bedrock (configurable model) | User specified; model selectable at runtime |
| Web Research | Tavily Search + Extract + Crawl APIs | User specified; all three capabilities enabled |
| CLI Interaction | Interactive REPL loop with streaming | Q6=B |
| Output Format | Single Markdown file per query | Q4=A |
| Credential Management | AWS credential chain (Bedrock) + TAVILY_API_KEY env var | Q5=D |
| Python Version | Python 3.12+ | Q7=D |
| Package Manager | uv | Q7=D |
| Logging | Verbose structured logging (file + console) | Q8=C |
| Security Extension | Fully enforced | Q9=A |
| PBT Extension | Partial enforcement (PBT-02,03,07,08,09) | Q10=B |
| PBT Framework | Hypothesis | Q10=B; Python standard |

---

## Out of Scope
- Web UI or API server
- Multi-user / authentication layer
- Persistent database or session storage
- Cloud deployment / infrastructure provisioning
- Real-time collaboration features
