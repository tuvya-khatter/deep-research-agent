# Deep Research Agent

An interactive CLI research tool powered by Strands Agents SDK, Amazon Bedrock, and Tavily.
Ask a research question; the agent runs web searches, reads what it finds, and writes a
Markdown report with the sources it actually used.

The whole project was built through **AI-DLC**, AWS's agent-driven development methodology,
inside Kiro — the AI wrote the specification, the code, and the test suite, with a human
approving each stage. That produced the second half of this repository:

## The Grounding Gate

While building this, I hit a failure AI-DLC's existing gates structurally cannot catch:
**when the same model writes both the code and the tests that judge it, a wrong assumption is
encoded identically in both, so the test agrees with the bug instead of catching it.**

The source-extraction code was the casualty. It was well-structured, passed its own generated
tests, and cleared every upstream approval gate — but against a real recorded Bedrock response
it returned **0 of 5** sources, silently. Reports would have shipped citing nothing.

So I added a stage to the AI-DLC lifecycle: **Grounding**, positioned between Code Generation
and Build & Test, deliberately *before* the model writes its test suite so the tests cannot
inherit the same unverified assumptions. Its governing rule is that **the source of truth for
any contract is never the model.**

| Artifact | Path |
|---|---|
| **Gate specification** (the rule pack Kiro loads) | [`.aidlc-rule-details/construction/grounding.md`](.aidlc-rule-details/construction/grounding.md) |
| Gate implementation | [`grounding/run_grounding_gate.py`](grounding/run_grounding_gate.py) |
| Emitted ledger (the verdict) | [`aidlc-docs/construction/grounding/grounding-ledger.md`](aidlc-docs/construction/grounding/grounding-ledger.md) |
| Recorded-real fixture | [`grounding/fixtures/sources_real.json`](grounding/fixtures/sources_real.json) |
| Reality-fixture tests | [`tests/test_grounding.py`](tests/test_grounding.py) |
| Original AI-generated code, preserved | [`grounding/original_extractor.py`](grounding/original_extractor.py) |

> The gate spec lives in `.aidlc-rule-details/`, a dotted directory, because that is where
> AI-DLC keeps all its phase rule packs — `grounding.md` sits as a peer to the built-in
> `code-generation.md` and `build-and-test.md`. Use `ls -a` or `Cmd+Shift+.` to see it.

### Running it

```bash
uv run python -m grounding.run_grounding_gate   # exits 1 when the gate blocks
uv run pytest tests/test_grounding.py -v
```

### What it found

Three boundaries where the generated code consumed a contract it does not own, all
**DIVERGENT** — the model had pattern-matched the Anthropic Messages format onto the
Strands/Bedrock shape:

| # | Generated code assumed | Reality (source of truth) |
|---|---|---|
| B1 | `result.messages` carries the full conversation history | Strands' `AgentResult` has no `messages` field at all — it exposes `message`, `metrics`, `state`, `stop_reason` |
| B2 | `block["type"] == "tool_result"` (Anthropic Messages format) | Blocks returned through Bedrock are keyed `text`, `toolResult`, `toolUse` — there is no `type` key |
| B3 | Every tool returns its payload under `results` | Tavily's tools emit three collections — `results`, `extractions`, `pages` |

Against the recorded fixture the original extractor found **0 of 5** sources; the grounded
rewrite finds **5 of 5**. Gate result: **BLOCKED** — the lifecycle did not advance to Build &
Test until the code matched reality.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- AWS credentials configured (env vars, `~/.aws/credentials`, or IAM role)
- Tavily API key

## Setup

```bash
# Install dependencies
uv sync --dev

# Set credentials
export TAVILY_API_KEY=your_tavily_api_key
# AWS credentials via standard chain (aws configure, env vars, or IAM role)
```

## Usage

```bash
# Start interactive session with defaults
uv run python -m deep_research_agent

# Specify model and output directory
uv run python -m deep_research_agent \
  --model us.anthropic.claude-3-7-sonnet-20250219-v1:0 \
  --output-dir ./research

# Tune Tavily parameters
uv run python -m deep_research_agent \
  --max-search-results 15 \
  --max-crawl-depth 3
```

### CLI Flags

| Flag | Default | Description |
|---|---|---|
| `--model` | `us.anthropic.claude-3-7-sonnet-20250219-v1:0` | Bedrock model ID |
| `--output-dir` | `./research-output` | Directory for Markdown output files |
| `--max-search-results` | `10` | Max results per Tavily search call (1–50) |
| `--max-crawl-depth` | `2` | Max depth per Tavily crawl call (1–5) |

### Session Commands

| Input | Action |
|---|---|
| Any text | Submit research query |
| `exit`, `quit`, `q` | End session |
| `Ctrl+D` | End session (EOF) |
| `Ctrl+C` | Exit immediately |

### Retry on Error

If a query fails, you are prompted:
```
Retry this query? [r=retry / s=skip]:
```
Type `r` to retry the same query, or `s` to skip.

## Output Files

Each completed query writes a Markdown file to `--output-dir`:

```
research-output/
  impact-of-ai-on-healthcare_20260525_143022.md
  quantum-computing-overview_20260525_150311.md
```

Each file contains: title, metadata table (model, tokens, session IDs), full research response, and cited sources.

## Logs

Rotating logs are written to `./logs/deep_research_agent.log` (10 MB max, 5 backups).

## Running Tests

```bash
uv run pytest
uv run pytest -m pbt          # property-based tests only
uv run pytest tests/test_grounding.py -v   # reality-fixture tests (see Grounding Gate above)
uv run pytest --cov=deep_research_agent --cov-report=term-missing
```

## AI-DLC Artifacts

The full methodology trail is in `aidlc-docs/` — `inception/` (requirements, user stories,
application design), `construction/` (functional design, code generation plans, the grounding
ledger), `operations/`, plus `aidlc-state.md` tracking phase progress and `audit.md` logging
every prompt, answer, and approval. The rule packs Kiro loads each phase are in
`.aidlc-rule-details/`.
