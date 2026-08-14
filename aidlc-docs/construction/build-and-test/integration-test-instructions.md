# Integration Test Instructions — Deep Research Agent

## Purpose

Integration tests verify that all components work together end-to-end against real external services (Amazon Bedrock and Tavily APIs). These tests require valid credentials and incur API costs.

**Important**: Run integration tests in a dedicated test environment, never in production.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.12+ with venv | `uv sync --dev` already run |
| `TAVILY_API_KEY` | Set in environment |
| AWS credentials | IAM permissions for Bedrock `InvokeModelWithResponseStream` on `us.anthropic.claude-3-7-sonnet-20250219-v1:0` |
| Bedrock model access | Enable `claude-3-7-sonnet` in your AWS account's Bedrock console |
| Output directory writable | Default: current directory |

### Verify Prerequisites

```bash
uv run python -c "
import boto3, os
key = os.environ.get('TAVILY_API_KEY', '')
print('TAVILY_API_KEY:', 'set' if key else 'MISSING')
creds = boto3.session.Session().get_credentials()
print('AWS credentials:', 'resolved' if creds else 'MISSING')
"
```

---

## Integration Test Scenarios

### Scenario 1: Credential Validation Flow

**Description**: Verify that the entry point correctly validates credentials on startup and exits cleanly when credentials are missing.

**Setup**:
```bash
# Temporarily unset to test failure path
unset TAVILY_API_KEY
```

**Test Steps**:
```bash
uv run python -m deep_research_agent
```

**Expected Result**: Program exits with a clear error message referencing `TAVILY_API_KEY`. Exit code non-zero. No stack trace exposed.

**Cleanup**:
```bash
export TAVILY_API_KEY=your_key
```

---

### Scenario 2: Single Query End-to-End (Streaming)

**Description**: Submit one research query and verify the full pipeline: CLI → Pipeline → Agent → Bedrock (streaming) → Tavily tools → OutputManager → Markdown file.

**Setup**:
```bash
export TAVILY_API_KEY=your_key
export AWS_PROFILE=your_profile  # or AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
mkdir -p /tmp/research-output
```

**Test Steps**:
```bash
uv run python -m deep_research_agent --output-dir /tmp/research-output
```

When the `> ` prompt appears, type:
```
What is the Strands Agents SDK and what are its key features?
```

**Expected Results**:
- Streaming response appears in the terminal, line by line.
- After completion, a confirmation message shows the output file path.
- A Markdown file exists at `/tmp/research-output/what-is-the-strands-agents-sdk-and-what-are-its-key-f_<timestamp>.md`
- The file contains all 8 required sections: title, metadata table, response, sources table, footer.
- Log file created at `research_agent.log` (or configured log directory).

**Verify Output File**:
```bash
ls /tmp/research-output/
cat /tmp/research-output/what-is-the-strands*.md
```

---

### Scenario 3: Multi-Query Session

**Description**: Submit multiple queries in one session and verify session context is maintained and each query produces its own output file.

**Test Steps**: Start the agent, then submit three queries in sequence:
```
> What is Amazon Bedrock?
[wait for completion]
> What are the main Tavily API endpoints?
[wait for completion]
> exit
```

**Expected Results**:
- Three Markdown output files created (one per query).
- Each file has a distinct filename based on the query slug.
- Session ends cleanly with no errors after `exit`.
- All 3 queries recorded in the log file.

---

### Scenario 4: Invalid Query Rejection

**Description**: Verify CLI-level validation rejects empty, whitespace-only, and single-word all-caps queries without invoking Bedrock.

**Test Steps**: Start the agent, then submit invalid queries:
```
>          [only spaces — press Enter]
> RESEARCH  [single word all-caps]
> q
```

**Expected Results**:
- Empty query: error message displayed, no Bedrock call made.
- `RESEARCH`: error message about query being too vague (RULE-QV-03), no Bedrock call.
- `q`: session exits cleanly.
- No output files created for invalid queries.

---

### Scenario 5: Session Exit Commands

**Description**: Verify all exit commands (`exit`, `quit`, `q`) terminate the session cleanly.

**Test Steps**: Start the agent three times, using a different exit command each time:
```bash
echo "exit" | uv run python -m deep_research_agent
echo "quit" | uv run python -m deep_research_agent
echo "q" | uv run python -m deep_research_agent
```

**Expected Results**: Each invocation exits cleanly with exit code 0. No error messages.

---

### Scenario 6: Tavily Search Tool Invocation

**Description**: Verify the agent actually invokes Tavily search during research and results appear in the output file's sources section.

**Test Steps**:
```bash
uv run python -m deep_research_agent --max-search-results 3
```
Submit query: `What is the capital of France?`

**Expected Results**:
- Sources section in the Markdown file contains at least one URL.
- Log file shows Tavily tool invocations.

---

### Scenario 7: Keyboard Interrupt (Partial Save)

**Description**: Verify that interrupting a running query with `Ctrl+C` either saves a partial output (if tokens were received) or exits cleanly.

**Test Steps**:
```bash
uv run python -m deep_research_agent --output-dir /tmp/research-output
```
Submit a long research query, then press `Ctrl+C` while the response is streaming.

**Expected Results**:
- If tokens were received: a Markdown file is saved with `[INCOMPLETE]` marker appended to the response.
- The REPL returns to the prompt (RULE-BEDROCK-02), not a crash.
- Log records the interruption.

---

## Run Integration Tests

There is no automated integration test suite (these require live credentials and incur costs). Execute scenarios manually in the order listed above.

```bash
# Start a session for manual integration testing
uv run python -m deep_research_agent --output-dir /tmp/research-integration-test
```

---

## Cleanup

```bash
# Remove integration test output files
rm -rf /tmp/research-output /tmp/research-integration-test

# Remove log files created during testing
rm -f research_agent.log research_agent.log.*
```

---

## Troubleshooting

### `botocore.exceptions.NoCredentialsError`
- **Cause**: AWS credentials not resolved.
- **Fix**: `export AWS_PROFILE=your-profile` or set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.

### `botocore.exceptions.ClientError: Access denied`
- **Cause**: IAM user/role lacks `bedrock:InvokeModelWithResponseStream` permission.
- **Fix**: Attach the `AmazonBedrockFullAccess` managed policy or add the specific action.

### `botocore.exceptions.ClientError: model not found`
- **Cause**: Bedrock model access not enabled in your AWS region.
- **Fix**: Open the Bedrock console → Model access → enable `Claude 3.7 Sonnet`.

### `tavily.errors.InvalidAPIKeyError`
- **Cause**: `TAVILY_API_KEY` is invalid or expired.
- **Fix**: Verify the key at the Tavily dashboard and re-export it.

### Output file not created
- **Cause**: Output directory not writable, or `OutputError` raised.
- **Fix**: Check permissions on `--output-dir`; review the log file for `OutputError` entries.
