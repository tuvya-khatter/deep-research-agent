# Application Design Plan

## Project Context
- **Project**: Deep Research Agent CLI
- **Tech Stack**: Python 3.12, uv, Strands Agents SDK, Amazon Bedrock, Tavily Search/Extract/Crawl, Hypothesis (PBT)
- **Key References**: requirements.md (FR-01 through FR-07, NFR-01 through NFR-06), stories.md (US-001 through US-013)

---

## Execution Checklist

### Phase 1 — Questions
- [x] Step 1: Answer all questions in this document
- [x] Step 2: Resolve any ambiguities
- [x] Step 3: Approve this plan

### Phase 2 — Artifact Generation
- [x] Step 4: Generate `aidlc-docs/inception/application-design/components.md`
- [x] Step 5: Generate `aidlc-docs/inception/application-design/component-methods.md`
- [x] Step 6: Generate `aidlc-docs/inception/application-design/services.md`
- [x] Step 7: Generate `aidlc-docs/inception/application-design/component-dependency.md`
- [x] Step 8: Generate `aidlc-docs/inception/application-design/application-design.md` (consolidated)
- [x] Step 9: Validate design completeness and consistency

---

## Identified Component Candidates

From requirements and user stories, the following functional areas need component representation:

| Area | Description |
|---|---|
| CLI / REPL Interface | Interactive loop, query input, streaming display, exit handling (US-002 through US-005, US-011, US-012) |
| Research Agent | Core Strands agent wired to Bedrock LLM; orchestrates tool calls and response synthesis (US-003, US-006) |
| Tavily Tools | Search, Extract, and Crawl integrations registered as Strands tools (FR-03, US-009) |
| Output Manager | Markdown file generation, filename sanitization, directory management (FR-05, US-006, US-007) |
| Configuration | CLI arg parsing, credential loading, model/output-dir defaults (FR-06, US-001, US-002) |
| Logging | Structured rotating log file, token/latency tracking, session correlation (NFR-02, US-013) |

---

## Application Design Questions

Please fill in the letter choice after each `[Answer]:` tag. Choose `X` and describe if no option fits.

---

### Section 1: Component Identification & Boundaries

#### Question 1
How should the three Tavily integrations (Search, Extract, Crawl) be organized as components?

A) Three separate tool classes — `TavilySearchTool`, `TavilyExtractTool`, `TavilyCrawlTool` — each its own module, all sharing a common base class or interface
B) One unified `TavilyTools` component that encapsulates all three tools in a single module with three distinct methods/classes inside
C) One `TavilyClient` wrapper component that provides a unified API over all three Tavily endpoints, with Strands tool registrations built on top
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

#### Question 2
How should the CLI interaction layer and session lifecycle be organized?

A) Single `CLI` component — handles REPL loop, query input/validation, streaming display, session start/exit, and `--model`/`--output-dir` arg parsing all in one component
B) Two components — `CLI` (REPL loop, streaming display, arg parsing) and `SessionManager` (session lifecycle, correlation IDs, multi-query tracking)
C) Three components — `CLI` (REPL, display), `SessionManager` (lifecycle), and `ConfigManager` (arg parsing, credential validation)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

#### Question 3
How should configuration and credential loading be handled?

A) Inline at startup — env vars and CLI args resolved directly in the entry point (`__main__.py`), no dedicated config component
B) Dedicated `Config` dataclass — a typed configuration object (using Python `dataclasses` or Pydantic) populated at startup and passed through the system
C) Dedicated `ConfigManager` class — responsible for loading, validating, and providing access to all configuration values (model ID, output dir, API keys, AWS region)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Section 2: Service Layer Design

#### Question 4
How should the core research orchestration be structured relative to the Strands agent?

A) Direct Strands usage — the `ResearchAgent` component IS the Strands agent; no additional orchestration layer
B) Thin wrapper — a `ResearchAgent` class wraps the Strands agent, adding session context (correlation ID, query metadata) and delegating all LLM/tool logic to Strands
C) Orchestrator service — a `ResearchOrchestrator` service sits above the Strands agent, managing pre/post-processing (input sanitization, output file trigger, error recovery), with the Strands agent handling only LLM + tool calls
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

#### Question 5
Should there be a dedicated service for coordinating the full research pipeline (Tavily calls → LLM synthesis → file output → logging), or should each component handle its own part when called by the agent?

A) Pipeline service — a `ResearchPipeline` or similar service owns the end-to-end flow: invokes the agent, captures streamed output, triggers file write, and records to log
B) No pipeline service — the Strands agent orchestrates tool calls autonomously; the CLI triggers the agent and the agent calls output/logging components directly via tools or callbacks
C) Event-driven — components communicate via callbacks/hooks registered on the Strands agent (e.g., on-complete triggers OutputManager, on-tool-call triggers Logger)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Section 3: Component Dependencies & Communication

#### Question 6
How should the `OutputManager` be invoked after a research run completes?

A) Called directly by the agent/orchestrator after the Strands run completes — synchronous call with the final response text
B) Registered as a Strands agent callback/hook — triggered automatically when the agent finishes generating a response
C) Called by the CLI after each query completes — CLI receives the full response from the agent and passes it to OutputManager
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

#### Question 7
How should structured logging be integrated across components?

A) Module-level logger — each component gets a standard Python `logging.getLogger(__name__)` logger; a root logger configuration wires everything to the rotating file handler at startup
B) Injected logger — a configured `Logger` instance is created at startup and injected into each component that needs it (constructor injection)
C) Singleton logger service — a `ResearchLogger` class manages the rotating file handler, structured formatting, and token/latency tracking; components call it directly via import
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Section 4: Design Patterns & Architectural Constraints

#### Question 8
What architectural pattern should the overall application follow?

A) Layered — clear separation into: CLI layer → Service/Orchestration layer → Tool/Integration layer → Infrastructure layer (logging, config, output)
B) Component-based — independent components with well-defined interfaces; no strict layering, components communicate directly
C) Pipes and filters — data flows through a research pipeline: query → search → extract/crawl → synthesize → output; each stage is a discrete step
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

#### Question 9
Should the Tavily tool components implement a shared base class or protocol to enable consistent error handling and future extensibility?

A) Yes — define a `BaseTavilyTool` abstract base class or `TavilyTool` Protocol with a standard `execute()` method signature and error handling contract
B) No — keep tools simple and independent; they share no interface beyond being registered as Strands tools
C) Duck-typed protocol only — no base class, but tools follow the same method naming convention by convention (not enforced at the type level)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

#### Question 10
How should errors from external APIs (Tavily, Bedrock) be propagated through the system?

A) Custom exception hierarchy — define `TavilyError`, `BedrockError`, etc. as specific exception classes; components catch and re-raise appropriately
B) Return-value error handling — components return result objects (e.g., `Result[T, Error]`) rather than raising exceptions; callers check for errors
C) Standard exceptions with structured logging — catch all external errors at the integration boundary, log them with context, and raise a single generic `ResearchAgentError` up the stack
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

Please fill in every `[Answer]:` tag and let me know when done.
