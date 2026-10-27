"""Agent tools. For now: web search with Tavily, limited to official sources."""

import logging

from tavily import (
    InvalidAPIKeyError,
    MissingAPIKeyError,
    TavilyClient,
    UsageLimitExceededError,
)

from src import config
from src.mock_responses import MOCK_SOURCES
from src.schemas import Source

logger = logging.getLogger(__name__)


class SearchError(Exception):
    """Raised with a message that is safe to show to the user; `code` as in LLMError."""

    def __init__(self, message: str, code: str = "search_failed") -> None:
        super().__init__(message)
        self.code = code


def _to_sources(results: list[dict]) -> list[Source]:
    """Convert raw Tavily results into Source objects with short snippets."""
    return [
        Source(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=r.get("content", "")[: config.MAX_SNIPPET_CHARS],
        )
        for r in results
        if r.get("url")
    ]


def search_web(query: str, max_results: int = config.RESULTS_PER_SEARCH) -> list[Source]:
    """Search official Colombian sources and return up to `max_results` sources."""
    if config.LLM_MODE == "mock":
        return _to_sources(MOCK_SOURCES[:max_results])

    try:
        response = TavilyClient(api_key=config.TAVILY_API_KEY).search(
            query,
            search_depth="basic",
            max_results=max_results,
            include_domains=config.TRUSTED_DOMAINS,
        )
    except (InvalidAPIKeyError, MissingAPIKeyError) as exc:
        raise SearchError("The Tavily API key is missing or invalid.", "config") from exc
    except UsageLimitExceededError as exc:
        raise SearchError(
            "The free web searches for this month are used up.", "search_limit"
        ) from exc
    except Exception as exc:
        raise SearchError("The web search failed. Please try again.") from exc

    sources = _to_sources(response.get("results", []))
    logger.info("search results=%d", len(sources))
    return sources
