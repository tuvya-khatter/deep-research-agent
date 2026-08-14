# Performance Test Instructions — Deep Research Agent

## Purpose

The Deep Research Agent is a single-user interactive CLI tool, not a server handling concurrent requests. Its performance profile is dominated by external API latency (Amazon Bedrock streaming, Tavily API calls) rather than throughput or concurrency. Formal load testing with JMeter or k6 is not applicable.

Performance validation focuses on:
1. **Response latency** — time from query submission to first streaming token.
2. **Session overhead** — startup time and per-query overhead excluding API latency.
3. **Memory footprint** — no unbounded growth across multiple queries.
4. **Log file growth** — rotating handler caps file size correctly.

---

## Performance Targets

| Metric | Target | Notes |
|---|---|---|
| Startup to first prompt | < 3 seconds | Credential resolution + component init |
| First token latency | < 5 seconds | Bedrock cold start + Tavily first call |
| Per-query overhead (excl. API) | < 200ms | Pipeline wiring, session bookkeeping |
| Memory growth per query | < 50 MB | Token buffer freed after each query |
| Log file max size | 10 MB per file | 5 rotated backups (configured in `logging_config.py`) |

---

## Test 1: Startup Time

**Description**: Measure time from invocation to first `> ` prompt appearing.

**Setup**:
```bash
export TAVILY_API_KEY=your_key
export AWS_PROFILE=your_profile
```

**Measurement**:
```bash
time (echo "exit" | uv run python -m deep_research_agent)
```

**Expected**: `real` time < 3 seconds (excluding cold starts of the Python interpreter on first run).

---

## Test 2: Per-Query Session Overhead

**Description**: Measure time spent in local Python code per query (excluding Bedrock and Tavily network latency) by comparing total query time to Bedrock-reported latency in the log.

**Method**:
1. Run a single query and record total wall-clock time.
2. Open `research_agent.log` and find the Bedrock invocation duration logged by `pipeline.py`.
3. Overhead = total time − Bedrock latency.

**Expected**: Overhead < 200ms.

---

## Test 3: Memory Growth — Multi-Query Session

**Description**: Verify that running many queries in one session does not cause unbounded memory growth. The token buffer in `ResearchPipeline._invoke_agent()` must be freed after each query.

**Setup**: Requires `memory-profiler` (install ad-hoc, not in project deps):
```bash
uv run pip install memory-profiler
```

**Run**:
```bash
uv run python -m memory_profiler -m deep_research_agent
```

Submit 5 queries in succession, then `exit`.

**Observation**: Memory should plateau after the first query and not increase linearly with each subsequent query. A < 50 MB increase per query is acceptable.

**Alternative (no profiler)**: Monitor with `top` or `Activity Monitor` during a 5-query session. RSS should not grow continuously.

---

## Test 4: Log File Rotation

**Description**: Verify that `RotatingFileHandler` caps log files at 10 MB and retains up to 5 backups.

**Verification**:
```bash
# After running several queries, check log sizes
ls -lh research_agent.log*
```

**Expected**: No single `research_agent.log` file exceeds 10 MB. Up to 5 rotated backup files (`research_agent.log.1` through `.5`) may exist.

**Note**: You can lower `maxBytes` temporarily in `logging_config.py` for faster rotation testing, then restore it.

---

## Test 5: Output File Write Time

**Description**: Verify that writing a Markdown output file completes in well under 1 second (this is a local file I/O operation with no network dependency).

**Method**:
```bash
# Enable DEBUG logging and check OutputManager write duration in log
uv run python -m deep_research_agent
```

After a query completes, search the log:
```bash
grep -i "output\|write" research_agent.log
```

**Expected**: File write completes in < 100ms.

---

## Baseline Measurements

Record actual measurements here after initial runs:

| Metric | Measured Value | Target | Status |
|---|---|---|---|
| Startup to first prompt | — | < 3s | — |
| First token latency | — | < 5s | — |
| Per-query overhead | — | < 200ms | — |
| Memory growth per query | — | < 50 MB | — |
| Max log file size | — | 10 MB | — |

---

## Performance Notes

- **Bedrock streaming latency** is outside the application's control. The agent uses streaming (`stream()` call) to show first tokens as soon as possible — this is already the lowest-latency Bedrock access pattern.
- **Tavily parallelism**: Each query may invoke multiple Tavily tools sequentially as the agent directs. The agent guides tool use order but does not parallelize calls — this is intentional for correctness.
- **Token buffer memory**: The `token_buffer` list in `_invoke_agent()` accumulates all tokens for a query (for partial-save support). For extremely long responses, this could grow large. Typical research responses are < 10,000 tokens, which is negligible (< 80 KB).
