# Business Rules — Deep Research Agent

## Sources
Derived from: functional-design-plan answers (Q1–Q17) + Security Baseline extension (SECURITY-03, SECURITY-05, SECURITY-09, SECURITY-11, SECURITY-12, SECURITY-15)

---

## Section 1 — Query Validation Rules (Q5, Q6)

### RULE-QV-01: Non-Empty After Strip
- Input after `.strip()` must not be empty
- Violation: display "Query cannot be empty." and re-prompt

### RULE-QV-02: Minimum Alphanumeric Content (Q5=C)
- The stripped query must contain at least one alphanumeric character
- Queries consisting only of whitespace, punctuation, or symbols are rejected
- Violation: display "Query must contain meaningful text." and re-prompt

### RULE-QV-03: Single-Word All-Caps Command Guard (Q5=C)
- A query that is a single whitespace-free token AND is entirely uppercase letters (A–Z only) is rejected
- Purpose: prevent accidental submission of exit-like commands (e.g., "EXIT", "QUIT", "HELP")
- This rule fires only if the query matches both conditions simultaneously
- Violation: display "Did you mean to type a command? If this is your query, please add context." and re-prompt

### RULE-QV-04: No Hard Max Length (Q6=D)
- No application-level maximum query length is enforced
- The Bedrock model's context window is the effective limit
- Rationale: user decision — avoid artificial truncation of complex research queries

---

## Section 2 — Exit Command Rules (Q4)

### RULE-EXIT-01: Recognized Exit Signals
The REPL exits cleanly when any of the following are received from `_get_query()`:
- User types `exit` (case-insensitive)
- User types `quit` (case-insensitive)
- User types `q` (case-insensitive, exact single character)
- `EOFError` is raised (Ctrl+D on Unix/Mac)
- `KeyboardInterrupt` is raised (Ctrl+C) — exits immediately without session close message

### RULE-EXIT-02: Exit During Retry Prompt
- If the user presses Ctrl+C or Ctrl+D during the retry/skip prompt, the session exits cleanly
- `exit`, `quit`, `q` typed at the retry prompt are treated as "skip" (not session exit)
- Rationale: exit commands at the retry prompt would be ambiguous; Ctrl+C is the unambiguous exit signal

---

## Section 3 — Error Recovery Rules (Q7)

### RULE-ERR-01: Session Resilience
- A `ResearchAgentError` MUST NOT terminate the REPL session
- After any research failure, the session continues to accept new queries

### RULE-ERR-02: Retry Prompt (Q7=C)
- After displaying the error message, the CLI prompts: `Retry this query? [r=retry / s=skip]: `
- Accepted inputs (case-insensitive):
  - `r` or `retry` → re-run the same query (new `QueryRecord`, same query text)
  - `s`, `skip`, or any other input → skip, return to `_get_query()`
- On retry: a new `QueryRecord` is created (new `query_id`) for the same `query_text`

### RULE-ERR-03: User-Facing Error Messages (SECURITY-09)
- Error messages shown to users MUST be generic — no stack traces, file paths, SDK internals, or exception class names
- Acceptable: "Research failed — web search unavailable. Please try again."
- Unacceptable: "TavilySearchError: HTTP 429 at https://api.tavily.com/search line 42 in tavily_tools.py"
- Full error detail (including `exc_info`) is logged at ERROR level in the rotating log file only

---

## Section 4 — Streaming Display Rules (Q8)

### RULE-STREAM-01: Line-Buffered Output
- Tokens are accumulated in an internal line buffer
- Buffer is flushed to stdout (with `flush=True`) when a newline character `\n` is detected in the token
- Content after the last `\n` in a token remains in the buffer until the next flush trigger
- On query completion, the buffer is flushed unconditionally

### RULE-STREAM-02: No Artificial Delay
- No sleep or delay is introduced between token writes
- Tokens are printed as fast as the Strands SDK delivers them

---

## Section 5 — System Prompt Rules (Q1, Q2, Q3)

### RULE-PROMPT-01: Structured System Prompt Required (Q1=B)
- Every `ResearchAgent.stream()` invocation assembles a structured system prompt at call time
- The prompt MUST include: date, session_id, query_id, tool descriptions, and research approach guidance

### RULE-PROMPT-02: Guided Tool Sequence (Q2=B)
- The system prompt MUST recommend this preferred sequence:
  1. Use `tavily_search` first to identify relevant sources
  2. Use `tavily_extract` on the most relevant URLs for full content
  3. Use `tavily_crawl` when deep site exploration is needed
- The Bedrock LLM is NOT forced to follow this sequence; it may deviate based on query type
- Rationale: autonomy preserved for specialized queries (e.g., "crawl this specific URL")

### RULE-PROMPT-03: Session Context Injection (Q3=C)
- `session_id` and `query_id` MUST appear in the system prompt (for traceability in agent reasoning logs)
- `session_id` and `query_id` MUST also appear in all structured log entries for the query [SECURITY-03]
- [SECURITY-12] API keys and AWS credentials MUST NEVER appear in any prompt or log output

---

## Section 6 — Output File Rules (Q9, Q10, Q11)

### RULE-OUT-01: Mandatory File Sections (Q9=C)
Every output Markdown file MUST contain all of the following sections in order:
1. H1 title: `# Research: {query_title}`
2. Horizontal rule
3. H2 metadata block as a table (query, model, timestamp, session_id, query_id, token counts, source count)
4. Horizontal rule
5. Research response body (`response_text`)
6. Horizontal rule
7. H2 sources section (numbered list of `[{title}]({url})` with optional description)
8. Footer: `*Generated by Deep Research Agent*`

### RULE-OUT-02: Filename Slug (Q10=A)
`_sanitize_slug(query)` MUST:
1. Lowercase the entire query string
2. Replace all whitespace sequences with a single hyphen `-`
3. Strip all characters that are not `[a-z0-9-]`
4. Collapse consecutive hyphens into one
5. Strip leading and trailing hyphens
6. Truncate to a maximum of 50 characters (truncate before stripping trailing hyphens)
7. If slug is empty after sanitization, use the fallback `"research"`

### RULE-OUT-03: Filename Format
`_build_filename(slug, timestamp)` MUST produce: `{slug}_{YYYYMMDD_HHMMSS}.md`
- `timestamp` is the UTC datetime at the start of `OutputManager.write()`
- Example: `impact-of-ai-on-healthcare_20260525_143022.md`

### RULE-OUT-04: Filename Collision Handling (Q11=B)
If `{slug}_{YYYYMMDD_HHMMSS}.md` already exists in `output_dir`:
- Append a 1-based counter: `{slug}_{YYYYMMDD_HHMMSS}_1.md`
- Increment counter until a non-colliding filename is found
- Counter cap: 999; if exceeded, raise `OutputError`

### RULE-OUT-05: Output Directory Creation
- `_ensure_output_dir(output_dir)` creates the directory (including parents) if it does not exist
- If creation fails due to permissions: raise `OutputError` with a user-friendly message [SECURITY-09]

---

## Section 7 — Logging Rules (Q14, Q15)

### RULE-LOG-01: Standard Per-Query Log Fields (Q14=B)
`ResearchPipeline._log_result()` MUST log at `INFO` level with these fields:
- `query_id` (str)
- `session_id` (str)
- `model_id` (str)
- `input_tokens` (int)
- `output_tokens` (int)
- `total_tokens` (int)
- `duration_seconds` (float, 2 decimal places)
- `source_count` (int)
- `output_path` (str, absolute)

### RULE-LOG-02: Sensitive Data Exclusion (SECURITY-03, SECURITY-12)
Log output MUST NEVER contain:
- `TAVILY_API_KEY` or any portion of it
- AWS access keys, secret keys, or session tokens
- Full query text (may appear in audit context but NOT in application logs)
- Any PII or user-supplied data beyond the `query_id` / `session_id` identifiers

### RULE-LOG-03: Rotating File Handler Parameters (Q15=B)
- Max file size: 10 MB (`maxBytes=10_485_760`)
- Backup count: 5
- Encoding: UTF-8
- Log file path: `{log_dir}/deep_research_agent.log`

### RULE-LOG-04: Log Levels
- Application startup events: INFO
- Per-query results: INFO
- Recoverable errors (Tavily partial failures): WARNING
- ResearchAgentError conditions: ERROR (with `exc_info=True`)
- Unexpected exceptions: ERROR (with `exc_info=True`)
- Debug detail (tool calls, prompt assembly): DEBUG

---

## Section 8 — Tavily Tool Parameter Rules (Q16, Q17)

### RULE-TAVILY-01: CLI-Configurable Defaults (Q16=B)
- `--max-search-results` CLI flag sets `TavilySearchTool.max_results` (default: 10, min: 1, max: 50)
- `--max-crawl-depth` CLI flag sets `TavilyCrawlTool.max_depth` (default: 2, min: 1, max: 5)
- Validation of these values occurs in `_parse_args()` with `argparse` type-checking
- Values are fixed per session; no per-query override

### RULE-TAVILY-02: Extract URL Retry (Q17=C)
For each URL in `ExtractInput.urls`:
- Attempt 1: call Tavily Extract API
- If HTTP error or timeout: attempt 2 immediately (no delay)
- If attempt 2 also fails: log WARNING with URL and error, mark URL as failed, continue to next URL
- If ALL URLs fail: raise `TavilyExtractError`
- If at least one URL succeeds: return `ExtractResult` with successful extractions only

### RULE-TAVILY-03: Partial Tavily Failure (Q12=D)
- Individual Tavily tool errors during agent execution are surfaced to the Strands SDK as tool errors
- The Strands SDK delivers the tool error to the Bedrock LLM as tool call feedback
- The LLM decides how to continue (use other tools, acknowledge limitation, conclude with available data)
- `ResearchPipeline` does not intercept individual tool errors; it handles only a final unrecovered `TavilyError`

---

## Section 9 — Bedrock Stream Interruption Rules (Q13)

### RULE-BEDROCK-01: Partial Save on Interruption (Q13=B)
If the Bedrock stream is interrupted after at least one token has been received:
- Append `\n\n---\n**[INCOMPLETE — stream interrupted]**` to the accumulated token buffer
- Return a synthetic `AgentResponse` with `is_complete=False`
- Proceed to write the partial response to a Markdown file (using the normal output flow)
- Log the interruption at ERROR level with `exc_info=True`
- Surface a `BedrockError` to `ResearchPipeline` after the partial save completes

If the stream is interrupted before any tokens are received:
- Raise `BedrockError` immediately; no partial output file is written

### RULE-BEDROCK-02: No Automatic Retry on Interruption
- Bedrock stream interruptions are NOT retried automatically
- The REPL's retry-or-skip prompt (RULE-ERR-02) gives the user the option to retry manually

---

## Section 10 — Security Rules (Cross-Cutting)

### RULE-SEC-LOGGING (SECURITY-03)
- Every component that performs external calls (ResearchAgent, TavilyTools, OutputManager) MUST use `logging.getLogger(__name__)`
- Log entries MUST include timestamp (automatic), correlation IDs (session_id, query_id), log level, and message
- See RULE-LOG-02 for sensitive data exclusions

### RULE-SEC-INPUT-VALIDATION (SECURITY-05)
- All user CLI input (query text) MUST pass through `_validate_query()` before being passed to any downstream component
- CLI args (`--model`, `--output-dir`, `--max-search-results`, `--max-crawl-depth`) MUST be validated by `argparse` with explicit types and constraints
- No raw user input is ever concatenated into system commands or file paths without sanitization

### RULE-SEC-ERROR-MESSAGES (SECURITY-09)
- User-facing error messages MUST be generic: describe the failure category without system internals
- Internal exception details are only in log files (which users must explicitly access)

### RULE-SEC-CREDENTIAL-ISOLATION (SECURITY-11, SECURITY-12)
- Credential validation logic is isolated to `__main__._validate_credentials()` — no credential reading elsewhere
- `TAVILY_API_KEY` is read once at startup, never stored beyond the tool constructors
- AWS credentials are accessed only through the SDK credential chain (boto3/botocore); never read directly
- No credentials appear in source code, configuration files, prompts, or logs

### RULE-SEC-FAIL-CLOSED (SECURITY-15)
- If `_validate_credentials()` fails at startup: print a user-friendly `ConfigurationError` message and exit with code 1
- If `_ensure_output_dir()` fails: raise `OutputError`; the query fails but the session continues
- All external calls (Bedrock, Tavily, file I/O) have explicit error handlers; no unhandled exceptions reach the user
- A top-level `except Exception` in `CLI.run()` is the final safety net: logs the error and exits gracefully

### RULE-SEC-MISUSE-SCENARIOS (SECURITY-11)
The following misuse scenarios have been considered in this design:

| Scenario | Mitigation |
|---|---|
| Attacker injects prompt into query text to exfiltrate API keys | API keys never appear in prompts (RULE-PROMPT-03); injected instructions cannot cause key disclosure |
| User submits extremely long query to exhaust Bedrock context | No hard limit by design (Q6=D); Bedrock returns an error which surfaces as `BedrockError` and is handled gracefully |
| User supplies a path traversal string as `--output-dir` | `Path(output_dir).resolve()` normalizes the path; directory creation is sandboxed to the resolved path |
| Tavily API key leaked in log | RULE-LOG-02 explicitly prohibits credential logging; `api_key` is never passed to loggers |
| Collision attack on output filenames | Counter suffix (RULE-OUT-04) prevents overwrite; counter cap raises `OutputError` at 999 collisions |
