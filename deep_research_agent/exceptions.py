"""Custom exception hierarchy for the Deep Research Agent.

All exceptions expose only a user-friendly message — no internal details.
"""


class ResearchAgentError(Exception):
    """Base exception for all Deep Research Agent errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(ResearchAgentError):
    """Raised when required credentials or configuration are missing or invalid."""


class BedrockError(ResearchAgentError):
    """Raised when the Amazon Bedrock LLM call fails."""


class TavilyError(ResearchAgentError):
    """Base class for Tavily API failures."""


class TavilySearchError(TavilyError):
    """Raised when the Tavily Search API call fails."""


class TavilyExtractError(TavilyError):
    """Raised when all URLs in a Tavily Extract call fail."""


class TavilyCrawlError(TavilyError):
    """Raised when the Tavily Crawl API call fails."""


class OutputError(ResearchAgentError):
    """Raised when writing the research output file fails."""
