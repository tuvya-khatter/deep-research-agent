# Security Test Instructions — Deep Research Agent

## Purpose

Verify compliance with the Security Baseline extension rules (SECURITY-01 through SECURITY-15) enforced across all project stages. Tests cover: credential handling, input validation, error message sanitization, dependency vulnerabilities, and secure coding patterns.

---

## Security Rules Tested

| Rule | Area | Test Method |
|---|---|---|
| SECURITY-03 | Application Logging | Log content inspection |
| SECURITY-05 | Input Validation | Boundary/injection testing |
| SECURITY-09 | Error Handling | Error message review |
| SECURITY-11 | Secure Design | Code inspection |
| SECURITY-12 | Credential Management | Log/output scanning |
| SECURITY-15 | Fail-Safe Defaults | Credential failure testing |

---

## Test 1: Dependency Vulnerability Scan (SECURITY-01 equivalent)

**Description**: Scan all dependencies for known CVEs.

**Run**:
```bash
# Install pip-audit (ad-hoc, not in project dev deps)
uv run pip install pip-audit

# Scan the project's dependencies
uv run pip-audit
```

**Alternatively with Safety**:
```bash
uv run pip install safety
uv run safety check
```

**Expected**: No critical or high severity CVEs in `strands-agents`, `boto3`, `tavily-python`, or `hypothesis`. Medium/low findings should be reviewed and documented.

**Fix process**: If a CVE is found, update the affected package in `pyproject.toml` to a patched version, then `uv sync --dev`.

---

## Test 2: No Credentials in Logs (SECURITY-03, SECURITY-12)

**Description**: Verify that API keys, AWS credentials, and access tokens never appear in log files.

**Setup**: Run a full integration test session (see `integration-test-instructions.md`), then inspect the log.

**Run**:
```bash
# Check for Tavily API key pattern (40-char alphanumeric starting with tvly-)
grep -E 'tvly-[A-Za-z0-9]{32,}' research_agent.log && echo "FAIL: API key in log" || echo "PASS"

# Check for AWS key patterns
grep -E 'AKIA[0-9A-Z]{16}' research_agent.log && echo "FAIL: AWS key in log" || echo "PASS"

# Check for "secret" or "password" near values
grep -iE '(secret|password|api_key|apikey)\s*[:=]\s*\S+' research_agent.log && echo "FAIL: credential in log" || echo "PASS"
```

**Expected**: All checks return `PASS`. The log must contain no credential values — only "set"/"resolved"/"missing" status indicators.

---

## Test 3: Input Validation — Query Injection (SECURITY-05)

**Description**: Verify that the CLI query validator rejects or safely handles potentially malicious inputs without passing them to system commands or exposing internals.

**Unit test coverage** (already in `test_cli.py`):
```bash
uv run pytest tests/test_cli.py -v -k "validate"
```

**Manual tests** — start the agent and submit:

| Input | Expected |
|---|---|
| `; rm -rf /` | Treated as a query string, passed to Bedrock, no shell execution |
| `<script>alert(1)</script>` | Treated as a query string, no HTML interpretation |
| `' OR 1=1 --` | Treated as a query string, no SQL execution |
| 5000-character query | Accepted (no upper length limit imposed) or rejected with validation message |
| Query with only special chars: `!@#$%^&*()` | RULE-QV-02: "no alphabetic/numeric characters" → rejected with error |

**Expected**: No shell execution, no file access, no exception traces exposed to the terminal. Only structured error messages.

---

## Test 4: Error Message Sanitization (SECURITY-09)

**Description**: Verify that error messages shown to the user never include stack traces, internal file paths, AWS account IDs, or raw exception details.

**Manual test**: Cause each error type deliberately and inspect terminal output.

**To trigger `BedrockError`**: Use an invalid AWS region:
```bash
AWS_DEFAULT_REGION=us-fake-1 uv run python -m deep_research_agent
```
Submit a query. Expected terminal output: a generic message like "Research failed. [r=retry / s=skip]". No boto3 stack trace.

**To trigger `TavilyError`**: Set an invalid API key:
```bash
TAVILY_API_KEY=invalid_key uv run python -m deep_research_agent
```
Submit a query. Expected terminal output: generic error, no raw Tavily exception detail.

**To trigger `OutputError`**: Set output directory to a read-only path:
```bash
uv run python -m deep_research_agent --output-dir /root/cannot-write
```
Submit a query. Expected terminal output: generic error about output failure, no `PermissionError` stack trace.

**Check log for detail**:
```bash
grep -i "error\|exception\|traceback" research_agent.log | head -20
```
Full details (including exception type) should appear in the log but NOT in terminal output.

---

## Test 5: Credential Validation Fail-Safe (SECURITY-15)

**Description**: Verify the application refuses to start when credentials are missing or invalid, rather than proceeding in a degraded state.

**Test A — Missing TAVILY_API_KEY**:
```bash
unset TAVILY_API_KEY
uv run python -m deep_research_agent
```
**Expected**: Exits immediately with a non-zero exit code and message about `TAVILY_API_KEY`. Does not show the `> ` prompt.

**Test B — Missing AWS credentials**:
```bash
AWS_PROFILE=nonexistent_profile uv run python -m deep_research_agent
```
**Expected**: Exits immediately with a non-zero exit code and message about AWS credentials.

**Verify exit code**:
```bash
echo $?
```
Must be non-zero (fail-closed behavior).

---

## Test 6: Credential Isolation (SECURITY-11, SECURITY-12)

**Description**: Verify that the `TAVILY_API_KEY` is read only in `__main__._validate_credentials()` and `tools/tavily_tools.py`, and is never passed as a string to logging, prompts, or the Bedrock agent system prompt.

**Static analysis**:
```bash
# Find all references to TAVILY_API_KEY or api_key in source
grep -rn "TAVILY_API_KEY\|api_key" deep_research_agent/ --include="*.py"
```

**Expected locations** (the only acceptable references):
- `__main__.py`: `os.environ.get("TAVILY_API_KEY")` and `if not tavily_key`
- `tools/tavily_tools.py`: `__init__(self, api_key: str)` and `TavilyClient(api_key=api_key)`

**Unacceptable locations**: `agent.py` system prompt, `logging_config.py`, `pipeline.py`, `cli.py`, any test file that logs the real key.

---

## Test 7: Secrets Not in Test Files

**Description**: Verify no hardcoded API keys or credentials in test fixtures.

```bash
grep -rn "tvly-\|AKIA\|secret" tests/ --include="*.py"
```

**Expected**: Only `conftest.py` contains a fixture `tavily_api_key` returning a fake value like `"tvly-test-key"` — no real credentials.

---

## Security Test Summary

| Test | SECURITY Rule | Status |
|---|---|---|
| Dependency scan | SECURITY-01 | Run and document |
| No credentials in logs | SECURITY-03, SECURITY-12 | Automated grep |
| Input injection | SECURITY-05 | Manual + unit tests |
| Error sanitization | SECURITY-09 | Manual |
| Fail-safe on missing credentials | SECURITY-15 | Manual |
| Credential isolation in code | SECURITY-11, SECURITY-12 | Static analysis |
| No secrets in tests | SECURITY-12 | Automated grep |

All tests must pass before marking the Security Baseline extension as compliant for the Build and Test stage.
