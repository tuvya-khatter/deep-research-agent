# Functional Design Plan — Deep Research Agent

## Unit: Deep Research Agent (Single Unit)

### Scope
CLI entry point · Strands agent setup · Bedrock LLM integration · Tavily tools (search, extract, crawl) · streaming output · session REPL loop · Markdown file generation · structured logging · session correlation IDs

---

## Plan Checkboxes

- [x] Step 1: Analyze unit context (application design artifacts)
- [x] Step 2: Generate clarifying questions
- [x] Step 3: Collect user answers
- [x] Step 4: Resolve any ambiguities (no blocking ambiguities found)
- [x] Step 5: Generate `business-logic-model.md`
- [x] Step 6: Generate `domain-entities.md`
- [x] Step 7: Generate `business-rules.md`
- [x] Step 8: Present completion message and await approval

---

## Clarifying Questions

Answer each question by replacing the `[Answer]:` line with your response.

---

### Section A — Agent Research Strategy

**Q1. System Prompt / Research Instructions**

The `ResearchAgent` wraps Strands with Bedrock and three tools (search, extract, crawl). What instructions or system prompt should guide the agent's research behavior?

A) Minimal — just pass the user query with no additional system instructions; let the model decide  
B) Structured — provide a system prompt with explicit instructions on research steps (e.g., "first search, then extract key pages, use crawl for deep dives")  
C) Template-based — provide a system prompt template with placeholders for query, session context, and date  
D) None — the user will supply custom system prompts at runtime via a CLI argument

[Answer]: B

---

**Q2. Tool Orchestration Strategy**

When the agent receives a research query, how should it decide which Tavily tools to use?

A) Fully autonomous — let the Bedrock LLM decide dynamically which tools to call and in what order  
B) Guided — system prompt recommends a preferred sequence (e.g., search first, then extract for top results) but allows deviation  
C) Enforced — the pipeline enforces a fixed call order; search always runs first before extract/crawl are available  
D) User-directed — user can hint in the query which tools to use (e.g., "crawl this site: ...")

[Answer]: B

---

**Q3. Session Context in Agent Calls**

The `session_context` dict (session_id, query_id) is passed to `ResearchAgent.stream()`. How should this be used?

A) Logging only — inject into structured log lines but NOT passed to the Strands agent prompt  
B) Prompt injection — include session/query IDs in the system prompt for traceability  
C) Both — inject into both log lines and the agent prompt  
D) Neither — only used internally in ResearchPipeline for constructing ResearchResult

[Answer]: C

---

### Section B — REPL Interaction Logic

**Q4. Exit Commands**

What commands should the CLI recognize as exit signals?

A) `exit` only  
B) `exit` and `quit`  
C) `exit`, `quit`, `q`, and `Ctrl+C` / `Ctrl+D` (EOF)  
D) Any of the above plus a configurable custom exit keyword

[Answer]: C

---

**Q5. Query Validation Rules**

Beyond non-empty and max-length, what validation should `_validate_query()` enforce?

A) None — non-empty + max-length is sufficient  
B) Reject queries that are only whitespace or punctuation (require at least one alphanumeric character)  
C) Reject queries that look like commands (e.g., single-word all-caps inputs) to prevent accidental submission  
D) Validate against a minimum meaningful length (e.g., at least 10 characters)

[Answer]: C

---

**Q6. Max Query Length**

What should the maximum query length be?

A) 500 characters  
B) 1,000 characters  
C) 2,000 characters  
D) No enforced limit (rely on Bedrock context window limits)

[Answer]: D

---

**Q7. Error Recovery in REPL**

When `ResearchPipeline.run()` raises a `ResearchAgentError` (e.g., Bedrock timeout, Tavily failure), what should happen in the REPL?

A) Display error message, continue to next prompt — session stays alive  
B) Display error message with specific error type, continue to next prompt  
C) Display error message, offer user the option to retry the same query or skip  
D) Display error message, terminate the session and exit

[Answer]: C

---

**Q8. Streaming Display Behavior**

During streaming, how should the CLI display tokens?

A) Print tokens directly to stdout as they arrive, no buffering  
B) Buffer by word (flush on space/punctuation) for cleaner display  
C) Buffer by line (flush on newline) for clean line-by-line output  
D) Print tokens with a brief delay between chunks for a "typing" effect

[Answer]: C

---

### Section C — Markdown Output Format

**Q9. Output File Structure**

What sections should the generated Markdown research file contain?

A) Minimal: just the agent's response text with a title header  
B) Standard: title + response text + sources section (list of URLs)  
C) Rich: title + metadata block (query, model, date, session/query IDs, token counts) + response text + sources section with titles and URLs  
D) Rich + summary: same as C but with an AI-generated executive summary at the top

[Answer]: C

---

**Q10. Filename Slug Rules**

For `_sanitize_slug()`, what should the slug rules be?

A) Lowercase, spaces → hyphens, strip non-alphanumeric (except hyphens), max 50 chars  
B) Lowercase, spaces → underscores, strip non-alphanumeric (except underscores), max 60 chars  
C) Lowercase, spaces → hyphens, strip non-alphanumeric (except hyphens), max 80 chars  
D) Lowercase, truncate at first 40 characters after basic sanitization

[Answer]: A

---

**Q11. Filename Collision Handling**

If a file with the same slug + timestamp already exists (e.g., two queries in the same second), what should `OutputManager` do?

A) Overwrite silently  
B) Append a counter suffix: `slug_YYYYMMDD_HHMMSS_1.md`, `..._2.md`, etc.  
C) Append microseconds: `slug_YYYYMMDD_HHMMSS_microseconds.md`  
D) Raise `OutputError` — treat collision as an error condition

[Answer]: B

---

### Section D — Partial Failure Handling

**Q12. Partial Tavily Failure**

If one Tavily tool call fails mid-research (e.g., `TavilyExtractError` on one URL) but the agent continues with other tools, what should happen to the output?

A) Write partial result — save whatever the agent produced; note the failure in the Markdown output  
B) Write partial result — save without noting the failure (failure logged separately)  
C) Abort the entire query — raise `ResearchAgentError`, do not write any output file  
D) Let Strands SDK decide — if the agent completes a response despite the tool error, write the full result

[Answer]: D

---

**Q13. Bedrock Stream Interruption**

If the Bedrock stream is interrupted mid-response (connection drop, timeout), what should happen?

A) Discard partial response, surface `BedrockError` to the user, continue REPL  
B) Save the partial response collected so far as the output file, mark it as "[INCOMPLETE]" in the file, continue REPL  
C) Retry once automatically, then surface `BedrockError` if second attempt also fails  
D) Surface `BedrockError` immediately, do not retry, do not write output

[Answer]: B

---

### Section E — Observability

**Q14. Structured Log Fields per Query**

What fields should be logged at `INFO` level when `ResearchPipeline._log_result()` runs?

A) Minimal: query_id, session_id, duration_seconds, output_path  
B) Standard: query_id, session_id, model_id, input_tokens, output_tokens, total_tokens, duration_seconds, source_count, output_path  
C) Verbose: all of B plus tool_calls (count, names), query_text (truncated to 100 chars), file size in bytes  
D) Custom — I will specify the fields

[Answer]: B

---

**Q15. Log Rotation Parameters**

What should the rotating file handler parameters be?

A) 5 MB max size, 3 backup files  
B) 10 MB max size, 5 backup files  
C) 50 MB max size, 10 backup files  
D) Configurable via CLI argument at startup

[Answer]: B

---

### Section F — Tavily Tool Parameters

**Q16. Configurable vs. Fixed Tool Parameters**

The application design defines defaults: `SearchInput.max_results=10` and `CrawlInput.max_depth=2`. Should users be able to override these?

A) Fixed defaults only — no user override, keep it simple  
B) Override via CLI flags (e.g., `--max-search-results`, `--max-crawl-depth`)  
C) Override per-query inline (e.g., user types a query with parameters embedded)  
D) Override via environment variables (`TAVILY_MAX_RESULTS`, `TAVILY_CRAWL_DEPTH`)

[Answer]: B

---

**Q17. Tavily Extract Partial Results**

When `TavilyExtractTool.execute()` receives a list of URLs and one URL fails to extract, should it:

A) Raise `TavilyExtractError` immediately — fail the whole batch  
B) Return partial results — include successful extractions, skip failed URLs, log the failures  
C) Retry each failed URL once, then return partial results with any remaining failures logged  
D) Let the Tavily API decide — return whatever the API returns without extra handling

[Answer]: B

---
