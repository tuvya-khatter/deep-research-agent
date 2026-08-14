# Code Summary — Deep Research Agent

## Generated Files

### Application Code (workspace root)

| File | Layer | Responsibility |
|---|---|---|
| `pyproject.toml` | Config | Project metadata, dependencies, entry point, tool config |
| `.gitignore` | Config | Excludes venv, logs, output, secrets |
| `README.md` | Docs | Usage guide, CLI flags, output format |
| `deep_research_agent/__init__.py` | Package | Version declaration |
| `deep_research_agent/types.py` | Shared | All shared dataclasses (16 types) |
| `deep_research_agent/exceptions.py` | Shared | Custom exception hierarchy (8 classes) |
| `deep_research_agent/logging_config.py` | Infrastructure | Rotating file + console logger setup |
| `deep_research_agent/tools/__init__.py` | Package | Tool package init |
| `deep_research_agent/tools/tavily_tools.py` | Tool Layer | BaseTavilyTool + 3 Tavily tool classes |
| `deep_research_agent/output.py` | Infrastructure | OutputManager — Markdown generation and file write |
| `deep_research_agent/agent.py` | Service | ResearchAgent — Strands SDK façade |
| `deep_research_agent/pipeline.py` | Service | ResearchPipeline — end-to-end query orchestration |
| `deep_research_agent/session.py` | CLI Layer | SessionManager, Session, QueryRecord |
| `deep_research_agent/cli.py` | CLI Layer | REPL loop, streaming display, validation, retry/skip |
| `deep_research_agent/__main__.py` | Entry Point | Arg parsing, credential validation, component wiring |

### Tests

| File | Type | Coverage |
|---|---|---|
| `tests/conftest.py` | Fixtures + Hypothesis strategies | Shared fixtures; 8 domain strategies |
| `tests/test_tools.py` | Example-based | All 3 Tavily tools, retry logic, error handling |
| `tests/test_output.py` | Example-based + **5 PBT** | OutputManager — slug, filename, format, write |
| `tests/test_agent.py` | Example-based | ResearchAgent — system prompt, streaming, error |
| `tests/test_pipeline.py` | Example-based + **1 PBT** | Pipeline — success, partial save, error surfacing |
| `tests/test_session.py` | Example-based + **3 PBT** | SessionManager — lifecycle, IDs, context dict |
| `tests/test_cli.py` | Example-based + **2 PBT** | CLI — validation, display, REPL, error recovery |

---

## Story Traceability

| Story | Files |
|---|---|
| US-001 Configure Credentials | `__main__._validate_credentials()` |
| US-002 Start Interactive Session | `__main__.main()`, `cli.CLI.run()`, `session.SessionManager` |
| US-003 Submit Query with Streaming | `cli.CLI._display_stream()`, `pipeline.ResearchPipeline.run()`, `agent.ResearchAgent.stream()` |
| US-004 Multiple Queries in One Session | `cli.CLI._repl()`, `session.SessionManager.add_query()` |
| US-005 Exit Session Cleanly | `cli.CLI._repl()` (exit command detection) |
| US-006 Receive Research as Markdown File | `output.OutputManager.write()`, `pipeline._save_output()` |
| US-007 Verify Sources and Metadata | `output.OutputManager._format_markdown()`, `agent._extract_sources()` |
| US-008 Handle Missing/Invalid Credentials | `__main__._validate_credentials()`, `exceptions.ConfigurationError` |
| US-009 Handle Tavily API Failure | `tools.tavily_tools.*`, `pipeline.ResearchPipeline` error boundary |
| US-010 Handle Bedrock Invocation Failure | `agent.ResearchAgent.stream()`, `pipeline.ResearchPipeline` error boundary |
| US-011 Handle Invalid/Empty Query | `cli.CLI._validate_query()` (RULE-QV-01/02/03/04) |
| US-012 Handle Interrupted Session | `pipeline._invoke_agent()` partial save (RULE-BEDROCK-01), `cli.CLI._repl()` KeyboardInterrupt |
| US-013 Access Research Log File | `logging_config.setup_logging()`, `pipeline._log_result()` |

---

## PBT Compliance Summary

| Rule | Status | Details |
|---|---|---|
| PBT-02 (Round-trip) | N/A | No serialization/deserialization pairs |
| PBT-03 (Invariant) | Compliant | 11 invariant property tests across 4 test files |
| PBT-07 (Generator Quality) | Compliant | 8 domain-specific Hypothesis strategies in conftest.py |
| PBT-08 (Shrinking/Reproducibility) | Compliant | Hypothesis default shrinking; seed logged on failure |
| PBT-09 (Framework) | Compliant | `hypothesis>=6.100.0` in pyproject.toml dev deps |

### PBT Tests by File

| File | Tests | Properties Verified |
|---|---|---|
| `test_output.py` | `test_property_sanitize_slug_length` | len(slug) ≤ 50 |
| | `test_property_sanitize_slug_charset` | chars in `[a-z0-9-]`, non-empty |
| | `test_property_sanitize_slug_idempotent` | sanitize(sanitize(x)) == sanitize(x) |
| | `test_property_format_markdown_sections` | all required sections always present |
| | `test_property_format_markdown_source_count` | source_count matches len(sources) |
| `test_pipeline.py` | `test_property_result_duration_non_negative` | duration_seconds ≥ 0 |
| `test_session.py` | `test_property_add_query_increments_count` | len(queries) == n calls |
| | `test_property_session_id_is_uuid4` | session_id is valid UUID4 |
| | `test_property_context_dict_keys` | dict has exactly {session_id, query_id} |
| `test_cli.py` | `test_property_validate_query_valid_inputs_never_raise` | valid queries pass without error |
| | `test_property_validate_query_empty_always_raises` | empty/whitespace always raises ValueError |

---

## Security Extension Compliance

| Rule | Status | Evidence |
|---|---|---|
| SECURITY-03 Application Logging | Compliant | `logging_config.py` (no credentials in format); `RULE-LOG-02` enforced in pipeline |
| SECURITY-05 Input Validation | Compliant | `cli._validate_query()` (RULE-QV-01–04); `_parse_args()` with type constraints |
| SECURITY-09 Error Handling | Compliant | Generic messages in `cli._display_error()`; pipeline raises generic `ResearchAgentError` |
| SECURITY-11 Secure Design | Compliant | Credentials isolated in `__main__._validate_credentials()` only |
| SECURITY-12 Credential Management | Compliant | `api_key` from env only; never logged; never in prompts (agent.py) |
| SECURITY-15 Fail-Safe Defaults | Compliant | `CLI.run()` KeyboardInterrupt + global except; fail-closed on credential failure |
