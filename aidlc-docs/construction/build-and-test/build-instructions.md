# Build Instructions — Deep Research Agent

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12+ | `python --version` |
| uv | Latest | `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| AWS credentials | — | Configured via env vars, `~/.aws/credentials`, or IAM role |
| Tavily API key | — | Set as `TAVILY_API_KEY` environment variable |

### Required Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TAVILY_API_KEY` | Yes | Tavily API key for web research tools |
| `AWS_ACCESS_KEY_ID` | No (if using profile/role) | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | No (if using profile/role) | AWS secret key |
| `AWS_PROFILE` | No | Named AWS profile to use |
| `AWS_REGION` | No | AWS region (default: us-east-1) |

---

## Build Steps

### 1. Clone / Enter the Project

```bash
cd /path/to/deep-research-agent
```

### 2. Install All Dependencies

```bash
# Install runtime + dev dependencies
uv sync --dev
```

Expected output: uv resolves and installs all packages from `pyproject.toml`.
A `.venv/` directory and `uv.lock` are created in the project root.

```bash
# Verify installation
uv run python -c "import deep_research_agent; print('OK')"
```

### 3. Configure Environment

```bash
# Required
export TAVILY_API_KEY=your_tavily_api_key

# AWS — choose one approach:
# Option A: Named profile
export AWS_PROFILE=your-profile

# Option B: Direct credentials
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1  # or your preferred region
```

### 4. Verify Credential Resolution

```bash
uv run python -c "
import boto3, os
key = os.environ.get('TAVILY_API_KEY', '')
print('TAVILY_API_KEY:', 'set' if key else 'MISSING')
creds = boto3.session.Session().get_credentials()
print('AWS credentials:', 'resolved' if creds else 'MISSING')
"
```

### 5. Install Package in Editable Mode (Optional — for IDE support)

```bash
uv pip install -e .
```

### 6. Verify Entry Point

```bash
uv run python -m deep_research_agent --help
```

Expected output: argument parser help text listing `--model`, `--output-dir`, `--max-search-results`, `--max-crawl-depth`.

---

## Build Artifacts

| Artifact | Location | Description |
|---|---|---|
| Virtual environment | `.venv/` | Isolated Python environment |
| Lock file | `uv.lock` | Pinned dependency versions (commit to VCS) |
| Installed package | `.venv/lib/python3.12/site-packages/deep_research_agent/` | Installed package |
| Entry point script | `.venv/bin/deep-research-agent` | Installed CLI script |

---

## Troubleshooting

### `uv sync` fails — Python version mismatch
- **Cause**: System Python < 3.12
- **Fix**: `uv python install 3.12` then `uv sync --dev`

### `ModuleNotFoundError: strands`
- **Cause**: `strands-agents` not installed or wrong environment
- **Fix**: Confirm inside venv: `uv run python -c "import strands"`; re-run `uv sync --dev`

### `ModuleNotFoundError: tavily`
- **Cause**: `tavily-python` not installed
- **Fix**: `uv add tavily-python` then `uv sync --dev`

### AWS `NoCredentialsError` at runtime
- **Cause**: No valid AWS credentials in the credential chain
- **Fix**: Run `aws configure` or export `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`

### `TAVILY_API_KEY` not set
- **Cause**: Environment variable missing
- **Fix**: `export TAVILY_API_KEY=your_key` — the agent will exit with a clear error if missing
