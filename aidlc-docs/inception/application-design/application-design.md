# Application Design — Consolidated

## Project: Deep Research Agent CLI

---

## 1. Architectural Overview

**Pattern**: Layered Architecture  
**Language**: Python 3.12+  
**Package Manager**: uv  
**Agent Framework**: Strands Agents SDK  
**LLM Provider**: Amazon Bedrock (configurable model)  
**Web Research**: Tavily Search + Extract + Crawl APIs  

### Layers

```
+-----------------------------------------------+
|              CLI LAYER                        |
|  CLI (REPL, display, arg parse)               |
|  SessionManager (lifecycle, correlation IDs)  |
+-----------------------------------------------+
|         SERVICE / ORCHESTRATION LAYER         |
|  ResearchPipeline (end-to-end flow owner)     |
|  ResearchAgent (Strands wrapper + Bedrock)    |
+-----------------------------------------------+
|         TOOL / INTEGRATION LAYER              |
|  TavilySearchTool                             |
|  TavilyExtractTool    (all extend             |
|  TavilyCrawlTool       BaseTavilyTool)        |
+-----------------------------------------------+
|           INFRASTRUCTURE LAYER                |
|  OutputManager (Markdown file generation)     |
|  LoggerSetup   (rotating structured logging)  |
|  exceptions    (custom exception hierarchy)   |
|  types         (shared data classes)          |
+-----------------------------------------------+
```

**Configuration**: No dedicated config component. CLI args (`--model`, `--output-dir`) parsed in `CLI`. Credentials (`TAVILY_API_KEY`, AWS credential chain) validated inline in `__main__.py` at startup.

---

## 2. Components

| Component | Module | Layer | Key Responsibility |
|---|---|---|---|
| `CLI` | `cli.py` | CLI | REPL loop, streaming display, query validation, arg parsing, exit handling |
| `SessionManager` | `session.py` | CLI | Session lifecycle, correlation IDs, per-query records |
| `ResearchPipeline` | `pipeline.py` | Service | End-to-end research flow: agent → output → log |
| `ResearchAgent` | `agent.py` | Service | Strands agent wrapper, Bedrock LLM, tool registration |
| `TavilySearchTool` | `tools/tavily_tools.py` | Tool | Tavily Search API, Strands tool registration |
| `TavilyExtractTool` | `tools/tavily_tools.py` | Tool | Tavily Extract API, Strands tool registration |
| `TavilyCrawlTool` | `tools/tavily_tools.py` | Tool | Tavily Crawl API, Strands tool registration |
| `OutputManager` | `output.py` | Infrastructure | Markdown generation, filename sanitization, file write |
| `LoggerSetup` | `logging_config.py` | Infrastructure | Root logger, rotating file handler, structured format |

**Exception Hierarchy** (`exceptions.py`):
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

---

## 3. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Tavily tool organization | One module, three classes sharing `BaseTavilyTool` | Cohesion — tools are always used together; base class enforces consistent interface and error contract |
| CLI / Session split | `CLI` + `SessionManager` as separate components | Single responsibility — display/input logic separated from lifecycle/correlation tracking |
| Config handling | Inline in `__main__.py` | Simplicity — single application, no runtime config changes; validates once at startup |
| Research orchestration | `ResearchPipeline` owns full flow above `ResearchAgent` | Clear ownership — one place for end-to-end error handling, output, and logging |
| OutputManager invocation | Called by `ResearchPipeline` (not CLI) | `ResearchPipeline` owns the full research result; CLI only renders and navigates |
| Logging integration | Module-level `logging.getLogger(__name__)` throughout | Standard Python practice — no coupling to a custom logger singleton |
| Error propagation | Custom exception hierarchy | Caller-specific error handling (retry vs. display vs. skip) without relying on string matching |

---

## 4. Module File Structure

```
deep_research_agent/
    __main__.py
    cli.py
    session.py
    pipeline.py
    agent.py
    output.py
    logging_config.py
    exceptions.py
    types.py
    tools/
        __init__.py
        tavily_tools.py
tests/
    test_cli.py
    test_session.py
    test_pipeline.py
    test_agent.py
    test_output.py
    test_tools.py
    conftest.py
pyproject.toml
uv.lock
logs/                    # created at runtime
research-output/         # created at runtime (default output dir)
```

---

## 5. Runtime Data Flow

```
Startup:
  __main__ validates credentials → sets up logging → wires all components → starts CLI

Per Query:
  CLI.get_query()
    → SessionManager.add_query()
    → ResearchPipeline.run(query, ctx, output_dir, stream_cb)
         → ResearchAgent.stream()          [Strands + Bedrock + Tavily tools]
               → tokens streamed → CLI displays
         → OutputManager.write()           [Markdown file]
         → logger.info(metrics)
    → CLI displays file path
    → back to prompt
```

---

## 6. Design Artifacts Reference

| Artifact | File |
|---|---|
| Component definitions | `components.md` |
| Method signatures | `component-methods.md` |
| Service definitions and interactions | `services.md` |
| Dependency matrix and data flow | `component-dependency.md` |
| This consolidated document | `application-design.md` |
