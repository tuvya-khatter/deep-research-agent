# Unit Test Execution — Deep Research Agent

## Overview

Unit tests are written with **pytest** and **Hypothesis** (property-based testing).
They run entirely in isolation with no network calls or AWS credentials required —
all external dependencies are mocked.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Virtual environment activated | `uv sync --dev` already run |
| No external credentials needed | All I/O is mocked in unit tests |

---

## Run Unit Tests

### 1. Execute All Unit Tests

```bash
uv run pytest tests/ -v
```

### 2. Execute with Coverage Report

```bash
uv run pytest tests/ --cov=deep_research_agent --cov-report=term-missing --cov-report=html -v
```

Coverage report is written to `htmlcov/index.html`.

### 3. Execute Property-Based Tests Only

```bash
uv run pytest tests/ -m pbt -v
```

### 4. Execute a Single Test File

```bash
# Tool layer
uv run pytest tests/test_tools.py -v

# Output manager
uv run pytest tests/test_output.py -v

# Research agent
uv run pytest tests/test_agent.py -v

# Pipeline
uv run pytest tests/test_pipeline.py -v

# Session manager
uv run pytest tests/test_session.py -v

# CLI
uv run pytest tests/test_cli.py -v
```

---

## Expected Results

| File | Tests | Type |
|---|---|---|
| `test_tools.py` | BaseTavilyTool abstract enforcement, TavilySearchTool, TavilyExtractTool (retry logic), TavilyCrawlTool, error propagation | Example-based |
| `test_output.py` | OutputManager slug sanitization, filename collision, Markdown format, file write | Example-based + 5 PBT |
| `test_agent.py` | ResearchAgent system prompt construction, streaming callback, source extraction, error handling | Example-based |
| `test_pipeline.py` | ResearchPipeline full flow, partial save on interruption, error boundary | Example-based + 1 PBT |
| `test_session.py` | SessionManager start/end session, add_query, UUID4 IDs, context dict | Example-based + 3 PBT |
| `test_cli.py` | CLI query validation, display stream, retry/skip flow, exit detection | Example-based + 2 PBT |

**Expected**: All tests pass, 0 failures.
**PBT tests**: 11 property-based tests across 4 files (marked `@pytest.mark.pbt`).

---

## Hypothesis Profiles

Two profiles are configured in `tests/conftest.py`:

| Profile | Examples per property | Usage |
|---|---|---|
| `default` | 50 | Local development |
| `ci` | 200 | CI pipelines |

```bash
# Run with CI profile (more examples)
uv run pytest tests/ -m pbt --hypothesis-profile=ci -v
```

On failure, Hypothesis prints the falsifying example and a seed for reproducibility:

```
Falsifying example: test_property_sanitize_slug_length(
    query='...'
)
You can reproduce this example by temporarily adding @reproduce_failure(...) to this test
```

---

## Linting and Type Checking

Run these alongside unit tests to catch additional issues:

```bash
# Ruff linting
uv run ruff check .

# Ruff formatting check
uv run ruff format --check .

# Mypy type checking
uv run mypy deep_research_agent/
```

---

## Fix Failing Tests

If tests fail:

1. Review pytest output — the failing test name and assertion message identify the issue.
2. For PBT failures: Hypothesis prints the minimal failing example.
   Use `@reproduce_failure` decorator to re-run the exact failing input.
3. Fix the source code (in `deep_research_agent/`) — never modify tests to hide failures.
4. Rerun: `uv run pytest tests/ -v`

---

## Troubleshooting

### `ImportError: No module named 'deep_research_agent'`
- **Cause**: Package not installed in the active venv.
- **Fix**: `uv pip install -e .` or `uv run pytest` (uv ensures the venv is used).

### `ImportError: No module named 'hypothesis'`
- **Cause**: Dev dependencies not installed.
- **Fix**: `uv sync --dev`

### `hypothesis.errors.InvalidArgument`
- **Cause**: Strategy constraint conflict in conftest.py.
- **Fix**: Review the strategy definition in `tests/conftest.py` and check Hypothesis version (`hypothesis>=6.100.0` required).

### Tests pass locally but fail in CI
- **Cause**: Hypothesis `default` profile uses fewer examples than `ci`.
- **Fix**: Run locally with `--hypothesis-profile=ci` to reproduce.
