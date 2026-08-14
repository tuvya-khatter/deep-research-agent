# Business Logic Model — Deep Research Agent

## Sources
Derived from: application-design artifacts + functional-design-plan answers (Q1–Q17)

---

## 1. Application Startup Flow

```
main()
  |
  +-- _parse_args()
  |     Parse: --model (required), --output-dir (default: ./research-output)
  |             --max-search-results (default: 10)
  |             --max-crawl-depth (default: 2)
  |
  +-- _validate_credentials()
  |     Check TAVILY_API_KEY env var -> ConfigurationError if missing/empty
  |     Check AWS credential chain   -> ConfigurationError if no valid credentials
  |     [SECURITY-12] Credentials read from env only, NEVER hardcoded
  |
  +-- setup_logging(log_dir, console_level, file_level)
  |     Create logs/ dir if absent
  |     Configure RotatingFileHandler (10 MB, 5 backups) [Q15]
  |     Configure StreamHandler (INFO to console)
  |
  +-- Construct components (dependency injection order):
  |     api_key = os.environ["TAVILY_API_KEY"]
  |     tools   = [TavilySearchTool(api_key, max_results),
  |                TavilyExtractTool(api_key),
  |                TavilyCrawlTool(api_key, max_depth)]
  |     agent   = ResearchAgent(model_id, tools)
  |     output_manager = OutputManager()
  |     pipeline       = ResearchPipeline(agent, output_manager)
  |     session_manager = SessionManager()
  |     cli     = CLI(pipeline, session_manager)
  |
  +-- cli.run(model_id, output_dir)
        [Blocks until user exits]
```

---

## 2. REPL Main Loop

```
CLI.run(model_id, output_dir)
  |
  +-- session = session_manager.start_session()
  |
  +-- Display welcome banner (tool names, model_id, exit commands)
  |
  +-- LOOP:
  |     query_raw = _get_query()           # blocks on input()
  |
  |     IF query_raw is None:              # EOF / Ctrl+D
  |         BREAK
  |
  |     IF query_raw.strip().lower() in {"exit", "quit", "q"}:
  |         BREAK
  |
  |     query = _validate_query(query_raw) # may raise ValueError
  |     IF ValueError:
  |         display error message, CONTINUE loop
  |
  |     query_record = session_manager.add_query(session, query)
  |     session_ctx  = session_manager.to_context_dict(session, query_record)
  |
  |     TRY:
  |         result = pipeline.run(query, session_ctx, output_dir,
  |                               stream_callback=_display_stream)
  |         _display_separator()
  |         _display_output_path(result.output_path)
  |
  |     EXCEPT ResearchAgentError as err:
  |         _display_error(err)
  |         choice = _prompt_retry_or_skip()  [Q7]
  |         IF choice == "retry":
  |             re-enter loop body with same query (goto top of loop, skip _get_query)
  |         ELSE:                             # skip
  |             CONTINUE loop
  |
  |     EXCEPT KeyboardInterrupt (Ctrl+C):   [Q4]
  |         BREAK
  |
  +-- session_manager.end_session(session)
  +-- Display goodbye message
  +-- EXIT
```

**Retry Mechanics (Q7=C):**
- After `ResearchAgentError`, CLI prints error with type + generic message [SECURITY-09]
- CLI prompts: `Retry this query? [r=retry / s=skip]: `
- Accepts `r`, `retry`, `s`, `skip` (case-insensitive)
- On `r` / `retry`: re-invokes `pipeline.run()` with the same query and a fresh `query_record`
- On `s` / `skip` or any other input: continues to next `_get_query()`

---

## 3. Per-Query Research Flow

```
ResearchPipeline.run(query, session_ctx, output_dir, stream_callback)
  |
  +-- start_time = time.monotonic()
  |
  +-- TRY:
  |     agent_response = _invoke_agent(query, session_ctx, stream_callback)
  |
  |     output_path = _save_output(agent_response, query, output_dir, session_ctx)
  |
  |     result = ResearchResult(
  |         query, agent_response.response_text, output_path,
  |         agent_response.sources, agent_response.token_usage,
  |         duration_seconds = time.monotonic() - start_time,
  |         session_id = session_ctx["session_id"],
  |         query_id   = session_ctx["query_id"],
  |         is_complete = agent_response.is_complete,   [Q13]
  |     )
  |     _log_result(result)
  |     RETURN result
  |
  +-- EXCEPT BedrockError:
  |     log ERROR with exc_info, session_ctx
  |     RAISE ResearchAgentError("Research failed — LLM unavailable")
  |
  +-- EXCEPT TavilyError:
  |     log ERROR with exc_info, session_ctx
  |     RAISE ResearchAgentError("Research failed — web search unavailable")
  |
  +-- EXCEPT OutputError:
  |     log ERROR with exc_info, session_ctx
  |     RAISE ResearchAgentError("Research failed — could not save output")
  |
  +-- EXCEPT Exception:
  |     log ERROR with exc_info, session_ctx
  |     RAISE ResearchAgentError("Research failed — unexpected error")
```

---

## 4. Agent Invocation and Streaming

```
ResearchPipeline._invoke_agent(query, session_ctx, stream_callback)
  |
  +-- token_buffer = []                    [Q13: accumulate for partial save]
  |
  +-- accumulating_callback = lambda token: (
  |       token_buffer.append(token),
  |       stream_callback(token)           # line-buffered display [Q8]
  |   )
  |
  +-- TRY:
  |     response = research_agent.stream(query, session_ctx, accumulating_callback)
  |     RETURN response                    # response.is_complete = True
  |
  +-- EXCEPT BedrockError:
  |     IF token_buffer is not empty:      [Q13=B: partial save]
  |         partial_text = "".join(token_buffer) + "\n\n---\n**[INCOMPLETE — stream interrupted]**"
  |         RETURN AgentResponse(
  |             response_text = partial_text,
  |             sources       = [],
  |             token_usage   = TokenUsage(0, 0, 0),
  |             tool_calls    = [],
  |             is_complete   = False,
  |         )
  |     ELSE:
  |         RAISE                          # no content at all: propagate
```

```
ResearchAgent.stream(query, session_ctx, callback)
  |
  +-- system_prompt = _build_system_prompt(session_ctx)  [Q1=B, Q2=B, Q3=C]
  |
  +-- Invoke Strands Agent with:
  |     - system_prompt
  |     - user message: query
  |     - registered tools: [tavily_search, tavily_extract, tavily_crawl]
  |     - stream callback: callback (forwards tokens as lines complete)
  |
  +-- On Strands/Bedrock SDK exception:
  |     Translate to BedrockError, RAISE
  |
  +-- On completion:
  |     Extract from Strands response:
  |       response_text  = full assembled text
  |       sources        = tool call results containing URLs
  |       token_usage    = from Strands/Bedrock usage metadata
  |       tool_calls     = list of ToolCallRecord from Strands event stream
  |     RETURN AgentResponse(..., is_complete=True)
```

---

## 5. System Prompt Structure (Q1=B, Q2=B, Q3=C)

The system prompt is assembled at call time with live context:

```
You are a deep research assistant with access to web research tools.

Date: {YYYY-MM-DD}
Session ID: {session_id}
Query ID:   {query_id}

Available tools:
- tavily_search:  Search the web for relevant sources on any topic
- tavily_extract: Extract full page content from specific URLs
- tavily_crawl:   Deep-crawl a site to explore linked pages

Recommended research approach (adapt as the query requires):
1. Begin with tavily_search to identify the most relevant sources
2. Use tavily_extract on the top results to get full content
3. Use tavily_crawl when deep exploration of a domain is needed

Produce a comprehensive, well-cited research response.
Structure your response with clear headers and sections.
Cite sources inline and include URLs.
```

---

## 6. Streaming Display (Q8=C — Line-Buffered)

```
CLI._display_stream(token)
  |
  +-- Append token to internal line buffer
  |
  +-- IF "\n" in token:
  |     Split on newlines
  |     Print all complete lines to stdout (flush=True)
  |     Keep remainder (after last \n) in buffer
  |
  +-- On REPL exit / query completion:
  |     Flush any remaining buffer content
```

**Rationale**: Line-buffering produces clean formatted output (headers, paragraphs) rather than character-by-character flicker.

---

## 7. Output File Generation Flow

```
ResearchPipeline._save_output(response, query, output_dir, session_ctx)
  |
  +-- metadata = OutputMetadata(
  |       query          = query,
  |       model_id       = self._model_id,
  |       session_id     = session_ctx["session_id"],
  |       query_id       = session_ctx["query_id"],
  |       generated_at   = datetime.utcnow(),
  |       source_count   = len(response.sources),
  |   )
  |
  +-- output_manager.write(
  |       response_text = response.response_text,
  |       query         = query,
  |       sources       = response.sources,
  |       metadata      = metadata,
  |       output_dir    = output_dir,
  |   )
  +-- RETURN output_path

OutputManager.write(response_text, query, sources, metadata, output_dir)
  |
  +-- _ensure_output_dir(output_dir)
  |
  +-- slug      = _sanitize_slug(query)         [Q10: max 50 chars, hyphens]
  +-- filename  = _build_filename(slug, now)    [Q11: collision counter]
  +-- content   = _format_markdown(response_text, sources, metadata)
  |
  +-- Write content to output_dir / filename
  +-- RETURN path
```

---

## 8. Tavily Tool Execution Flows

### TavilySearchTool.execute(SearchInput)
```
  +-- Call Tavily Search API with query + max_results
  +-- EXCEPT TavilySearchError: RAISE
  +-- RETURN SearchResult(results=[SearchItem(url, title, snippet, score), ...])
```

### TavilyExtractTool.execute(ExtractInput)  [Q17=C: per-URL retry once]
```
  +-- FOR each url in input.urls:
  |     TRY: extract url
  |     EXCEPT: TRY again once
  |     EXCEPT again: log warning, mark url as failed, CONTINUE
  +-- IF all urls failed: RAISE TavilyExtractError
  +-- RETURN ExtractResult(extractions=[ExtractionItem(url, content, metadata), ...])
       (failed URLs omitted from results; failures logged)
```

### TavilyCrawlTool.execute(CrawlInput)
```
  +-- Call Tavily Crawl API with url + max_depth
  +-- EXCEPT TavilyCrawlError: RAISE
  +-- RETURN CrawlResult(pages=[CrawledPage(url, content, depth), ...])
```

### Partial Tavily Failure Mid-Research (Q12=D)
Tavily tool errors surface as `TavilyError` subclasses through the Strands event stream.
The Strands SDK delivers the tool error to the LLM; the LLM decides whether to continue
research with remaining tools or to conclude with available information.
`ResearchPipeline` does not intercept individual tool errors — it handles only the
final `TavilyError` raised if the SDK propagates it after the agent gives up.
