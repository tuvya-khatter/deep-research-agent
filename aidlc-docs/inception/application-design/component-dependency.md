# Component Dependencies

## Dependency Matrix

| Component | Depends On | Type |
|---|---|---|
| `__main__` | `CLI`, `SessionManager`, `ResearchPipeline`, `ResearchAgent`, `OutputManager`, `TavilyTools`, `LoggerSetup`, `exceptions` | Composition root |
| `CLI` | `ResearchPipeline`, `SessionManager` | Constructor injection |
| `SessionManager` | *(none)* | Standalone |
| `ResearchPipeline` | `ResearchAgent`, `OutputManager` | Constructor injection |
| `ResearchAgent` | `BaseTavilyTool` (list), Strands SDK, Bedrock (external) | Constructor injection + external |
| `TavilySearchTool` | `BaseTavilyTool`, Tavily API (external) | Inheritance + external |
| `TavilyExtractTool` | `BaseTavilyTool`, Tavily API (external) | Inheritance + external |
| `TavilyCrawlTool` | `BaseTavilyTool`, Tavily API (external) | Inheritance + external |
| `OutputManager` | *(none)* | Standalone |
| `LoggerSetup` | Python stdlib `logging` | Standalone |
| All components | `exceptions`, `types`, `logging.getLogger` | Shared utilities |

---

## Dependency Graph

```
__main__.py  (composition root)
    |
    +---> LoggerSetup.setup_logging()
    |
    +---> TavilySearchTool(api_key)   --[inherits]--> BaseTavilyTool
    +---> TavilyExtractTool(api_key)  --[inherits]--> BaseTavilyTool
    +---> TavilyCrawlTool(api_key)    --[inherits]--> BaseTavilyTool
    |
    +---> ResearchAgent(model_id, tools=[Search, Extract, Crawl])
    |         |
    |         +---> Strands SDK  ---> Amazon Bedrock (external)
    |         +---> TavilyTools  ---> Tavily API (external)
    |
    +---> OutputManager()
    |
    +---> ResearchPipeline(agent, output_manager)
    |
    +---> SessionManager()
    |
    +---> CLI(pipeline, session_manager)
              |
              +---> [runtime] ResearchPipeline.run()
              +---> [runtime] SessionManager.start/add/end_session()
```

---

## Data Flow: Single Research Query

```
User types query
      |
      v
CLI._validate_query()
      |
      v
SessionManager.add_query()
      |
      v
ResearchPipeline.run(query, session_context, output_dir, stream_callback)
      |
      +---> ResearchAgent.stream(query, session_context, callback)
      |           |
      |           +---> [Strands autonomously calls tools as needed]
      |           |           |
      |           |           +--> TavilySearchTool.execute()  --> Tavily Search API
      |           |           +--> TavilyExtractTool.execute() --> Tavily Extract API
      |           |           +--> TavilyCrawlTool.execute()   --> Tavily Crawl API
      |           |
      |           +---> [tokens stream via callback --> CLI._display_stream() --> stdout]
      |           |
      |           +---> returns AgentResponse (text, sources, token_usage)
      |
      +---> OutputManager.write(text, query, sources, metadata, output_dir)
      |           |
      |           +--> writes {slug}_{timestamp}.md
      |           +--> returns Path
      |
      +---> logger.info(token_usage, latency, source_count, file_path)
      |
      +---> returns ResearchResult to CLI
      |
      v
CLI._display_separator()
CLI._display_output_path(path)
      |
      v
User sees result path; session returns to query prompt
```

---

## Coupling Analysis

| Coupling | Type | Notes |
|---|---|---|
| `CLI` ↔ `ResearchPipeline` | Loose — interface-based | CLI only calls `pipeline.run()` |
| `CLI` ↔ `SessionManager` | Loose | CLI only calls 3 methods |
| `ResearchPipeline` ↔ `ResearchAgent` | Loose — typed interface | Pipeline calls `agent.stream()` only |
| `ResearchPipeline` ↔ `OutputManager` | Loose | Pipeline calls `output_manager.write()` only |
| `ResearchAgent` ↔ `TavilyTools` | Loose — `BaseTavilyTool` contract | Agent receives list of tools; Strands dispatches |
| `ResearchAgent` ↔ Strands SDK | Tight — direct SDK usage | Intentional; Strands is the agent framework |
| `TavilyTools` ↔ Tavily API | Tight — HTTP calls | Intentional; Tavily is external dependency |
| All ↔ `exceptions` | Shared | Exception hierarchy is a shared contract |
| All ↔ `logging` | Shared stdlib | Module-level loggers via `logging.getLogger` |

---

## External Dependencies

| External System | Used By | Protocol |
|---|---|---|
| Amazon Bedrock | `ResearchAgent` via Strands SDK | AWS SDK (boto3 / Strands Bedrock provider) |
| Tavily Search API | `TavilySearchTool` | HTTPS / REST |
| Tavily Extract API | `TavilyExtractTool` | HTTPS / REST |
| Tavily Crawl API | `TavilyCrawlTool` | HTTPS / REST |

---

## Module File Structure

```
deep_research_agent/
    __main__.py              # Entry point: arg parsing, credential validation, wiring
    cli.py                   # CLI + REPL
    session.py               # SessionManager, Session, QueryRecord
    pipeline.py              # ResearchPipeline, ResearchResult
    agent.py                 # ResearchAgent, AgentResponse
    output.py                # OutputManager, OutputMetadata, Source
    logging_config.py        # setup_logging()
    exceptions.py            # Exception hierarchy
    types.py                 # Shared data types (TokenUsage, ToolCallRecord)
    tools/
        __init__.py
        tavily_tools.py      # BaseTavilyTool, Search, Extract, Crawl tools
```
