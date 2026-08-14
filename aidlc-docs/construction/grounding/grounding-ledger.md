# Grounding Ledger — deep_research_agent/agent.py

*Emitted by the Grounding Gate (Construction → between Code Generation and Build & Test).*
*Source of truth is never the model: installed type stubs + one recorded-real response.*

## Boundaries

| # | Location | Assumed (generated code) | Reality (source of truth) | Verdict |
|---|---|---|---|---|
| B1 | `agent._extract_sources` | result.messages  (result carries full history) | AgentResult fields = ['interrupts', 'message', 'metrics', 'state', 'stop_reason', 'structured_output']; has "messages"? False | 🔴 DIVERGENT |
| B2 | `agent._extract_sources` | block["type"] == "tool_result"  (Anthropic Messages format) | real block keys = ['text', 'toolResult', 'toolUse']; has "type"? False | 🔴 DIVERGENT |
| B3 | `agent._parse_sources` | every tool returns {"results": [...]} | tools emit collections ['extractions', 'pages', 'results']; code handles ['results'] | 🔴 DIVERGENT |

## Reality fixture test

- Recorded-real fixture: `grounding/fixtures/sources_real.json` — **5 real sources**
- Original AI-generated extractor → **0 sources**  ❌ FAIL
- Grounded (fixed) extractor → **5 sources**  ✅ PASS

## Gate result: ❌ BLOCKED
