# Deep Research Agent

An interactive CLI research tool powered by Strands Agents SDK, Amazon Bedrock, and Tavily. Built as part of the AWS AI-DLC Workshop.

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
uv run pytest --cov=deep_research_agent --cov-report=term-missing
```
