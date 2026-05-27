"""Entry point for the Deep Research Agent.

Responsibilities: arg parsing, credential validation, logging setup, component wiring.
Credentials are read from environment variables only — never hardcoded (SECURITY-12).
Error messages for missing credentials are actionable but contain no sensitive values (SECURITY-09).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from deep_research_agent.cli import CLI
from deep_research_agent.exceptions import ConfigurationError
from deep_research_agent.logging_config import setup_logging
from deep_research_agent.output import OutputManager
from deep_research_agent.pipeline import ResearchPipeline
from deep_research_agent.agent import ResearchAgent
from deep_research_agent.session import SessionManager
from deep_research_agent.tools.tavily_tools import (
    TavilySearchTool,
    TavilyExtractTool,
    TavilyCrawlTool,
)

_DEFAULT_MODEL = "us.anthropic.claude-sonnet-4-6"
_DEFAULT_OUTPUT_DIR = Path("./research-output")
_DEFAULT_LOG_DIR = Path("./logs")


def main() -> None:
    """Application entry point."""
    args = _parse_args()

    try:
        setup_logging(log_dir=_DEFAULT_LOG_DIR)
    except OSError:
        print("Warning: could not initialise log file. Logging to console only.", file=sys.stderr)

    try:
        api_key = _validate_credentials()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc.message}", file=sys.stderr)
        sys.exit(1)

    tools = [
        TavilySearchTool(api_key=api_key, max_results=args.max_search_results),
        TavilyExtractTool(api_key=api_key),
        TavilyCrawlTool(api_key=api_key, max_depth=args.max_crawl_depth),
    ]
    agent = ResearchAgent(model_id=args.model, tools=tools)
    output_manager = OutputManager()
    pipeline = ResearchPipeline(agent=agent, output_manager=output_manager)
    session_manager = SessionManager()
    cli = CLI(pipeline=pipeline, session_manager=session_manager)

    cli.run(model_id=args.model, output_dir=args.output_dir)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="deep-research-agent",
        description="Interactive CLI deep research agent powered by Amazon Bedrock and Tavily.",
    )
    parser.add_argument(
        "--model",
        default=_DEFAULT_MODEL,
        help=f"Bedrock model ID to use (default: {_DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        dest="output_dir",
        help=f"Directory for Markdown output files (default: {_DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--max-search-results",
        type=int,
        default=10,
        choices=range(1, 51),
        metavar="N",
        dest="max_search_results",
        help="Maximum Tavily search results per call, 1–50 (default: 10)",
    )
    parser.add_argument(
        "--max-crawl-depth",
        type=int,
        default=2,
        choices=range(1, 6),
        metavar="N",
        dest="max_crawl_depth",
        help="Maximum Tavily crawl depth, 1–5 (default: 2)",
    )
    return parser.parse_args()


def _validate_credentials() -> str:
    """Validate TAVILY_API_KEY and AWS credential chain.

    Returns the Tavily API key on success.
    Raises ConfigurationError with an actionable message on failure.
    Credentials are never included in error messages (SECURITY-09, SECURITY-12).
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        raise ConfigurationError(
            "Missing required environment variable: TAVILY_API_KEY\n"
            "  Set it with: export TAVILY_API_KEY=your_api_key"
        )

    try:
        import boto3
        session = boto3.session.Session()
        credentials = session.get_credentials()
        if credentials is None:
            raise ConfigurationError(
                "No AWS credentials found.\n"
                "  Options:\n"
                "    • Run: aws configure\n"
                "    • Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY environment variables\n"
                "    • Set AWS_PROFILE to a configured profile"
            )
        # Resolve to catch expired/invalid credential chains early
        resolved = credentials.get_frozen_credentials()
        if not resolved.access_key:
            raise ConfigurationError(
                "AWS credentials appear empty or invalid.\n"
                "  Run: aws configure  or check your AWS_PROFILE setting."
            )
    except ConfigurationError:
        raise
    except Exception:
        raise ConfigurationError(
            "Could not resolve AWS credentials.\n"
            "  Run: aws configure  or set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY."
        )

    return api_key


if __name__ == "__main__":
    main()
