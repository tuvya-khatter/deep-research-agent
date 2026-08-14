# Services

## Service Definitions

Two services form the orchestration layer. All other components are either integration adapters (tools), infrastructure utilities (output, logging), or UI components (CLI, session).

---

## Service 1: ResearchPipeline

**Module**: `deep_research_agent/pipeline.py`  
**Pattern**: Pipeline / Orchestrator  
**Layer**: Service / Orchestration

### Purpose
Owns the complete research lifecycle for a single user query. The CLI delegates all research work to this service; the CLI's only responsibility beyond handing off the query is rendering the streamed tokens and reporting the output file path.

### Responsibilities
1. Accept a query, session context, output directory, and streaming callback from the CLI
2. Invoke `ResearchAgent.stream()`, forwarding tokens via the callback
3. Collect the completed `AgentResponse` (full text, sources, token usage)
4. Invoke `OutputManager.write()` to persist the Markdown file
5. Log the result (query, model, token counts, latency, source count, file path)
6. Return a `ResearchResult` to the CLI
7. Catch `TavilyError` and `BedrockError` — log the error, surface a user-friendly message, and raise `ResearchAgentError` for the CLI to display; never crash the session

### Interactions
```
CLI
 └─calls─> ResearchPipeline.run(query, session_context, output_dir, stream_callback)
               └─calls─> ResearchAgent.stream()      [LLM + tools]
               └─calls─> OutputManager.write()       [file output]
               └─logs via module logger               [observability]
               └─returns ResearchResult to CLI
```

### Error Contract
- `BedrockError` → caught here, logged, re-raised as `ResearchAgentError`
- `TavilyError` → caught here, logged, result may be partial (partial sources noted in output), re-raised as `ResearchAgentError`
- `OutputError` → caught here, logged, re-raised as `ResearchAgentError`
- All other unexpected exceptions → logged at ERROR level, re-raised

---

## Service 2: ResearchAgent

**Module**: `deep_research_agent/agent.py`  
**Pattern**: Façade / Thin Wrapper  
**Layer**: Service / Orchestration

### Purpose
Wraps the Strands Agents SDK `Agent` to provide a clean, typed interface for the rest of the application. Insulates `ResearchPipeline` from Strands SDK internals.

### Responsibilities
1. Construct a Strands `Agent` configured with the Amazon Bedrock provider and selected model ID
2. Register all three `TavilyTool` instances as available tools on the Strands agent at construction time
3. Accept a research query and session context; invoke the Strands agent
4. Forward streamed tokens to the provided callback as they arrive
5. Extract token usage, tool call records, and source metadata from the Strands response
6. Return a typed `AgentResponse`
7. Translate Strands/Bedrock SDK exceptions into `BedrockError`

### Interactions
```
ResearchPipeline
 └─calls─> ResearchAgent.stream(query, session_context, callback)
               └─uses─> Strands Agent SDK
                           └─calls─> TavilySearchTool.execute()   [via Strands tool dispatch]
                           └─calls─> TavilyExtractTool.execute()
                           └─calls─> TavilyCrawlTool.execute()
               └─returns AgentResponse
```

### Error Contract
- Strands / Bedrock SDK errors → translated to `BedrockError` and raised
- Individual Tavily tool failures → `TavilyError` subclasses propagate through Strands and are surfaced to `ResearchPipeline`

---

## Entry Point Composition (`__main__.py`)

The entry point is not a service but is responsible for wiring all components together. It is the only place where configuration is read and components are instantiated.

```
__main__.main()
  1. _parse_args()                        → model_id, output_dir
  2. _validate_credentials()              → raises ConfigurationError if invalid
  3. setup_logging(log_dir, ...)          → configures root logger
  4. tools = [TavilySearchTool(api_key),
              TavilyExtractTool(api_key),
              TavilyCrawlTool(api_key)]
  5. agent = ResearchAgent(model_id, tools)
  6. output_manager = OutputManager()
  7. pipeline = ResearchPipeline(agent, output_manager)
  8. session_manager = SessionManager()
  9. cli = CLI(pipeline, session_manager)
 10. cli.run(model_id, output_dir)
```

---

## Service Interaction Summary

| Caller | Callee | Method | Purpose |
|---|---|---|---|
| `__main__` | `CLI` | `run()` | Start REPL loop |
| `CLI` | `SessionManager` | `start_session()` | Begin session |
| `CLI` | `SessionManager` | `add_query()` | Record each query |
| `CLI` | `ResearchPipeline` | `run()` | Execute research |
| `CLI` | `SessionManager` | `end_session()` | Close session |
| `ResearchPipeline` | `ResearchAgent` | `stream()` | LLM + tool invocation |
| `ResearchPipeline` | `OutputManager` | `write()` | Save Markdown file |
| `ResearchAgent` | `TavilySearchTool` | `execute()` | Web search (via Strands) |
| `ResearchAgent` | `TavilyExtractTool` | `execute()` | Page extraction (via Strands) |
| `ResearchAgent` | `TavilyCrawlTool` | `execute()` | Deep crawl (via Strands) |
