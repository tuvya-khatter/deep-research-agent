# Requirements Clarification Questions

Please answer each question by filling in the letter choice after the `[Answer]:` tag.
If none of the options match your needs, choose the last option (Other/X) and describe your preference.
Let me know when you are done.

---

## Question 1
Which Amazon Bedrock model(s) should the agent use for reasoning and generation?

A) Claude 3.5 Sonnet (claude-3-5-sonnet) — best balance of speed and capability
B) Claude 3.7 Sonnet (claude-3-7-sonnet) — latest with extended thinking support
C) Claude 3 Opus (claude-3-opus) — highest capability, slower
D) Make the model configurable at runtime (user can choose model via CLI arg or config)
X) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 2
Which Tavily API capabilities should the agent use?

A) Search only — use Tavily Search API to find relevant URLs and snippets
B) Search + Extract — use Search to find URLs, then Extract API to get full page content
C) Search + Crawl — use Search to find URLs, then Crawl API to deep-crawl linked pages
D) All three — Search, Extract, and Crawl used together for comprehensive research
X) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 3
How should the research depth and breadth be controlled?

A) Fixed depth — always fetch a fixed number of sources (e.g., top 10 results per query)
B) Configurable per session — user specifies depth/breadth at the start of each research session via CLI prompts
C) Agent-driven — the agent autonomously decides how many sources and sub-queries are needed based on topic complexity
D) Both B and C — configurable defaults with agent autonomy within those bounds
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 4
How should research output files be organized?

A) Single file per research session — one Markdown file per topic/query
B) Multi-file per session — separate files for summary, sources, findings, citations
C) Timestamped directory per session — a folder per research run containing multiple Markdown files
D) Configurable — user specifies output path and format at runtime
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 5
How should API credentials (Bedrock region/profile, Tavily API key) be managed?

A) Environment variables only — credentials loaded from env vars (AWS_REGION, TAVILY_API_KEY, etc.)
B) Config file — credentials stored in a YAML/TOML config file
C) Both — env vars take precedence, config file as fallback
D) AWS profiles + env vars — use standard AWS credential chain for Bedrock, env var for Tavily
X) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 6
How should the interactive CLI session work?

A) Single-query mode — user provides one research topic per invocation, agent runs and exits
B) Interactive loop — agent enters a REPL-like session where user can ask multiple research questions
C) Both — single-query mode via CLI args, interactive loop when no args provided
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 7
What Python version and packaging approach should be used?

A) Python 3.11+ with pip and requirements.txt
B) Python 3.11+ with Poetry for dependency management
C) Python 3.12+ with pip and pyproject.toml (PEP 517)
D) Python 3.12+ with uv for fast dependency management
X) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 8
What level of logging and observability is needed?

A) Minimal — only print research progress/status to the CLI; no log files
B) Standard — structured logging to a rotating log file plus CLI progress output
C) Verbose — detailed debug logging with timing metrics, token usage, and source tracking
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 9: Security Extension
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)
B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 10: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)
B) Partial — enforce PBT rules only for pure functions and serialization round-trips
C) No — skip all PBT rules (suitable for simple CRUD applications or thin integration layers)
X) Other (please describe after [Answer]: tag below)

[Answer]: B
