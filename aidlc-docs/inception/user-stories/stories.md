# User Stories

## Organization: User Journey-Based
Stories follow the research workflow end-to-end across six journey phases.

**Format**: Classic — "As a [persona], I want [goal] so that [benefit]"  
**Granularity**: Medium-grained — one story per meaningful capability  
**Acceptance Criteria**: Comprehensive — happy path, edge cases, error conditions  
**NFRs**: Excluded — captured separately in requirements.md  
**Internal agent behavior**: Excluded — stories cover user-visible inputs and outputs only  

---

## Phase 1: First-Run & Credential Setup

---

### US-001 — Configure Agent Credentials

**As a researcher**, I want to configure my AWS credentials and Tavily API key before running the agent, so that the agent can connect to Amazon Bedrock and Tavily APIs without error.

**Personas**: Alex (primary), Morgan (primary)

**Acceptance Criteria**:

*Happy Path*
- Given I have set the `TAVILY_API_KEY` environment variable and configured AWS credentials via the standard AWS credential chain (env vars, `~/.aws/credentials`, or IAM role), when I launch the agent, then the agent starts successfully without any credential error
- Given the agent starts successfully, when I submit a research query, then the agent executes without authentication failures

*Edge Cases*
- Given I have multiple AWS profiles configured, when I launch the agent with `AWS_PROFILE=my-profile`, then the agent uses that profile for Bedrock access
- Given I have both env-var credentials (`AWS_ACCESS_KEY_ID`) and a credentials file, when I launch the agent, then env-var credentials take precedence

*Error Conditions*
- Given `TAVILY_API_KEY` is not set, when I launch the agent, then the agent exits immediately with a clear message: "Missing required environment variable: TAVILY_API_KEY" and does not enter the interactive session
- Given no valid AWS credentials are resolvable, when I launch the agent, then the agent exits immediately with a clear message identifying the missing credential and does not enter the interactive session
- Given `TAVILY_API_KEY` is set to an empty string, when I launch the agent, then the agent treats it as missing and exits with the same credential error message

---

## Phase 2: Session Management

---

### US-002 — Start Interactive Research Session

**As a researcher**, I want to start an interactive CLI session with optional configuration flags, so that I can submit research queries and have the agent ready to work with my preferred settings.

**Personas**: Alex (primary), Morgan (primary)

**Acceptance Criteria**:

*Happy Path*
- Given all credentials are valid, when I run `python -m deep_research_agent` (or the installed entry point), then the agent displays a welcome/prompt message and waits for my first query
- Given I launch with `--model claude-3-5-sonnet-v2`, when the session starts, then all LLM calls in that session use the specified model
- Given I launch with `--output-dir ./my-research`, when the session starts, then all output files are written to `./my-research/` (created if it does not exist)
- Given I launch without any flags, when the session starts, then the agent uses the default model and default output directory (`./research-output/`)

*Edge Cases*
- Given I launch with an unrecognized `--model` value, when I submit a query, then the agent returns a clear error message listing supported model IDs and does not crash the session
- Given the specified `--output-dir` does not exist, when the session starts, then the agent creates the directory automatically without error

*Error Conditions*
- Given I launch with `--help`, then the agent prints usage instructions (supported flags, defaults, example invocation) and exits cleanly
- Given I launch with an unknown flag, then the agent prints usage instructions with a note about the unrecognized flag and exits cleanly

---

### US-003 — Submit a Research Query with Streaming Output

**As a researcher**, I want to submit a research query and see the synthesized response stream to my terminal in real time, so that I can start reading insights immediately without waiting for the full research to complete.

**Personas**: Alex (primary), Morgan (primary)

**Acceptance Criteria**:

*Happy Path*
- Given I am in an active session, when I type a research query and press Enter, then the agent begins outputting text to the terminal within a reasonable time and the output continues streaming until the response is complete
- Given the response is streaming, when the stream ends, then the terminal displays a clear visual separator and returns to the query prompt
- Given the research completes, then a Markdown output file is written to the configured output directory (see US-006)

*Edge Cases*
- Given I submit a very broad or complex query, when the agent is researching, then streaming output begins and the response reflects the broader scope (more synthesized content)
- Given I submit a very narrow or specific query, when the agent responds, then the output is appropriately concise

*Error Conditions*
- Given a Bedrock or Tavily failure occurs mid-stream, when the error is encountered, then the agent outputs a user-facing error message and returns to the query prompt without crashing the session (see US-009, US-010)

---

### US-004 — Run Multiple Queries in One Session

**As a researcher**, I want to submit multiple research queries in the same interactive session, so that I can efficiently explore related topics without restarting the agent.

**Personas**: Alex (primary), Morgan (primary)

**Acceptance Criteria**:

*Happy Path*
- Given a session is active, when I submit a second query after the first completes, then the agent processes the new query independently and produces a new output file
- Given I submit three queries in one session, then three separate Markdown output files are created — one per query — each with a unique filename
- Given each query completes, then the agent returns to the query prompt and is immediately ready to accept the next query

*Edge Cases*
- Given I submit a follow-up query that references the previous topic, when the agent processes it, then it treats it as an independent research task (no cross-query memory unless the agent explicitly supports it)

*Error Conditions*
- Given one query fails (e.g., API error), when I submit the next query, then the session continues normally and the failure of the prior query does not affect the new one

---

### US-005 — Exit Session Cleanly

**As a researcher**, I want to exit the research session when I am done, so that I know the session ended without errors and all completed output files are intact.

**Personas**: Alex (primary), Morgan (primary)

**Acceptance Criteria**:

*Happy Path*
- Given I am at the query prompt, when I type `exit` or `quit` and press Enter, then the agent prints a goodbye/exit message and terminates cleanly
- Given I press `Ctrl+C` at the query prompt (not during research), when the signal is received, then the agent exits cleanly with a brief message

*Edge Cases*
- Given I type `exit` with extra whitespace (e.g., `  exit  `), when I press Enter, then the agent still exits cleanly (whitespace-trimmed matching)

*Error Conditions*
- Given I press `Ctrl+C` during an active research run, then the agent terminates the in-progress query, prints a message indicating the research was interrupted, and exits cleanly (see US-012)
- Given the session exits for any reason, then previously completed output files from that session remain intact and are not deleted or corrupted

---

## Phase 3: Research Execution

---

### US-006 — Receive Research as a Markdown File

**As a researcher**, I want each research query to produce a well-structured Markdown file in a known location, so that I can review, share, or archive my research results.

**Personas**: Alex (primary), Morgan (primary)

**Acceptance Criteria**:

*Happy Path*
- Given a query completes successfully, then a `.md` file is written to the output directory
- Given the output file is created, then it contains at minimum: a title derived from the query, an executive summary section, a detailed findings section, a sources/citations section with URLs, and a metadata section (timestamp, model used)
- Given the file naming convention, then the filename follows the pattern `{sanitized-slug}_{YYYYMMDD_HHMMSS}.md` (e.g., `quantum-computing-overview_20260525_143022.md`)
- Given two queries with the same topic submitted at different times, then each produces a uniquely named file (timestamp ensures uniqueness)

*Edge Cases*
- Given a query topic contains special characters (e.g., `What is C++?`), when the file is created, then the filename slug is sanitized (special characters replaced or removed) and the file is created without error
- Given the output directory does not exist at the time a query completes, then the agent creates the directory and writes the file successfully

*Error Conditions*
- Given the output directory is not writable (permissions error), when a query completes, then the agent displays a clear error message identifying the path and permission issue; the session continues and the next query may succeed if a different directory is used

---

### US-007 — Verify Research Sources and Metadata

**As a researcher**, I want the research output file to include cited sources with URLs and generation metadata, so that I can assess research quality, verify claims, and follow up on specific references.

**Personas**: Alex (secondary), Morgan (primary)

**Acceptance Criteria**:

*Happy Path*
- Given a completed output file, then the Sources section lists each source with: a title or description, the URL, and (where available) a brief note on what information was drawn from it
- Given a completed output file, then the Metadata section includes: the research query as submitted, the timestamp of generation, the Bedrock model ID used, and the number of sources consulted
- Given the sources section, then all listed URLs are the actual URLs accessed by the agent (not fabricated)

*Edge Cases*
- Given the agent found only a small number of sources for a narrow topic, then the sources section still lists all sources consulted (even if fewer than typical)
- Given a source URL is very long, then it is still included in full in the sources section (not truncated)

*Error Conditions*
- Given the agent could not retrieve content from some sources, then those sources are either excluded from the list or flagged with a note indicating retrieval failed — they are not listed as successfully consulted sources

---

## Phase 4: Error Handling & Edge Cases

---

### US-008 — Handle Missing or Invalid Credentials

**As a researcher**, I want to receive a clear, actionable error message when my credentials are missing or invalid, so that I know exactly what to configure before retrying.

**Personas**: Alex (primary), Morgan (primary)

**Acceptance Criteria**:

*Happy Path*
- Given valid credentials, when the agent starts, then no credential-related messages are shown to the user

*Error Conditions*
- Given `TAVILY_API_KEY` is not set, when I launch the agent, then the error message specifies: which environment variable is missing, and how to set it — the agent does not enter the interactive session
- Given AWS credentials are missing or expired, when I launch the agent, then the error message specifies the AWS credential issue and suggests resolution steps (e.g., run `aws configure` or check `AWS_PROFILE`) — the agent does not enter the interactive session
- Given a Tavily API key is set but is invalid (rejected by Tavily), when I submit my first query, then the agent displays a clear error message stating the API key was rejected, the session returns to the prompt, and the agent does not crash
- Given AWS credentials are valid at startup but expire mid-session, when a Bedrock call is made, then the agent displays a clear authentication error and the session returns to the prompt

---

### US-009 — Handle Tavily API Failure

**As a researcher**, I want the agent to handle Tavily API failures gracefully and notify me, so that I understand my research may be incomplete but can continue using the session.

**Personas**: Alex (secondary), Morgan (primary)

**Acceptance Criteria**:

*Happy Path*
- Given all Tavily API calls succeed, then no error messages related to Tavily are shown

*Error Conditions*
- Given a Tavily Search API call fails (network error, rate limit, or server error), when the failure occurs, then the agent displays a user-facing message indicating web search was unavailable; the research attempt is terminated gracefully and the session returns to the query prompt
- Given a Tavily Extract API call fails for one or more URLs, when the failure occurs, then the agent continues with available content and the output file notes which sources could not be extracted
- Given a Tavily Crawl API call fails, when the failure occurs, then the agent continues without crawl data and the output file notes the crawl was unavailable
- Given repeated Tavily failures, when the agent retries, then the user sees that a retry is occurring; after exhausting retries the agent reports failure and returns to the prompt — it does not hang indefinitely

---

### US-010 — Handle Bedrock Invocation Failure

**As a researcher**, I want to receive a clear error message when the AI model fails to respond, so that I can retry my query or take a different approach.

**Personas**: Alex (primary), Morgan (primary)

**Acceptance Criteria**:

*Error Conditions*
- Given a Bedrock invocation fails (throttling, service error, or invalid request), when the failure occurs, then the agent displays a clear message identifying the failure type (e.g., "Model invocation was throttled — please retry") and returns to the query prompt without crashing the session
- Given the model ID specified at launch does not exist in Bedrock, when the first query is submitted, then the agent displays a clear error message listing the invalid model ID and suggesting the user check supported model IDs
- Given the Bedrock service is unavailable (5xx error), when the failure occurs, then the agent displays a user-facing service unavailability message and returns to the prompt

---

### US-011 — Handle Invalid or Empty Query

**As a researcher**, I want to receive a helpful message when I submit an empty or malformed query, so that I understand what a valid query looks like and can correct my input.

**Personas**: Alex (primary), Morgan (primary)

**Acceptance Criteria**:

*Happy Path*
- Given I submit a well-formed natural-language query, then the agent begins processing without validation errors

*Error Conditions*
- Given I press Enter without typing a query (empty input), when the Enter key is received, then the agent displays a brief prompt asking for a research topic and returns to the query input — it does not start a research run
- Given I submit a query that consists only of whitespace, then the agent treats it as empty input and behaves as above
- Given I submit a query that exceeds a maximum length, then the agent displays a message indicating the query is too long and specifies the maximum length; the session returns to the prompt

---

### US-012 — Handle Interrupted Session

**As a researcher**, I want the agent to exit gracefully when my session is interrupted, so that any completed output files are preserved and my terminal is left in a clean state.

**Personas**: Alex (primary), Morgan (secondary)

**Acceptance Criteria**:

*Error Conditions*
- Given I press `Ctrl+C` while a research query is in progress, when the interrupt signal is received, then the agent stops the in-progress query, displays a message indicating the research was interrupted, and exits the session — it does not hang
- Given the session is interrupted mid-research, then any output files from previously completed queries in the same session are preserved intact
- Given the session exits due to an interrupt, then the terminal cursor and prompt are restored to normal (no leftover escape codes or broken state)
- Given the process is killed externally (e.g., `kill`), then the output directory is not left with partially written files that would corrupt future reads

---

## Phase 5: Observability

---

### US-013 — Access Research Log File

**As a technical researcher**, I want to access a detailed log file after a research session, so that I can review token usage, API call timing, and diagnose any issues that occurred.

**Personas**: Alex (primary)

**Acceptance Criteria**:

*Happy Path*
- Given a research session completes, then a log file exists at a known, documented location (default: `./logs/research-agent.log`)
- Given I open the log file, then each log entry includes: an ISO 8601 timestamp, a log level, a session/correlation ID, and a message
- Given I ran multiple queries in a session, then the log file contains entries for each query, identifiable by the session correlation ID or a per-query identifier
- Given a query completed, then the log file records: the Bedrock model used, the number of input and output tokens, the wall-clock duration of the query, and the number of Tavily API calls made

*Edge Cases*
- Given I run multiple sessions over time, then the log file contains entries from all sessions, with older entries preserved (rotating log, not overwritten each run)
- Given the log file grows large, then log rotation is applied automatically so disk space is not exhausted

*Error Conditions*
- Given the log directory is not writable, then the agent displays a warning at startup but continues running — logging failures must not prevent the agent from functioning
- Given a session ends abnormally, then the log file still contains all entries up to the point of failure, providing a diagnostic trail

---

## Story Summary

| ID | Title | Phase | Personas |
|---|---|---|---|
| US-001 | Configure Agent Credentials | First-Run | Alex, Morgan |
| US-002 | Start Interactive Session | Session Management | Alex, Morgan |
| US-003 | Submit Query with Streaming Output | Research Execution | Alex, Morgan |
| US-004 | Run Multiple Queries in One Session | Session Management | Alex, Morgan |
| US-005 | Exit Session Cleanly | Session Management | Alex, Morgan |
| US-006 | Receive Research as Markdown File | Output Management | Alex, Morgan |
| US-007 | Verify Research Sources and Metadata | Output Management | Alex (sec), Morgan |
| US-008 | Handle Missing or Invalid Credentials | Error Handling | Alex, Morgan |
| US-009 | Handle Tavily API Failure | Error Handling | Alex (sec), Morgan |
| US-010 | Handle Bedrock Invocation Failure | Error Handling | Alex, Morgan |
| US-011 | Handle Invalid or Empty Query | Error Handling | Alex, Morgan |
| US-012 | Handle Interrupted Session | Error Handling | Alex, Morgan (sec) |
| US-013 | Access Research Log File | Observability | Alex |

**Total**: 13 stories across 5 journey phases, 2 domain personas
