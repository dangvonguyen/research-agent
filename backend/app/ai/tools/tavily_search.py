import asyncio
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field
from tavily import AsyncTavilyClient

from app.ai.tools.base import BaseTool
from app.core.config import settings
from app.types import ToolResultOutput as ToolOutput

logger = logging.getLogger(__name__)


class TavilySearchInput(BaseModel):
    """Input schema for TavilySearchTool."""

    queries: list[str] = Field(
        description="List of search queries to execute. Each query will be searched independently and results will be combined."
    )
    max_results: int = Field(
        default=5,
        description="Maximum number of results to return per query (default: 5)",
        ge=1,
        le=20,
    )
    search_depth: Literal["basic", "advanced"] = Field(
        default="basic",
        description="Search depth: 'basic' for quick results or 'advanced' for comprehensive search (default: basic)",
    )
    include_domains: list[str] | None = Field(
        default=None,
        description="Optional list of domains to specifically include in the search (e.g., ['arxiv.org', 'aclanthology.org, 'scholar.google.com'])",
    )
    exclude_domains: list[str] | None = Field(
        default=None,
        description="Optional list of domains to exclude from the search (e.g., ['wikipedia.org'])",
    )
    include_answer: bool = Field(
        default=True,
        description="Whether to include a summary answer in the response (default: true)",
    )
    include_raw_content: bool = Field(
        default=False,
        description="Whether to include raw page content in results (default: false)",
    )


class TavilySearchTool(BaseTool):
    """Tool for searching the web using Tavily API.

    This tool performs web searches using Tavily's search API, supporting:
    - Multiple parallel queries
    - Configurable search depth (basic or advanced)
    - Domain filtering (include/exclude)
    - Raw content extraction
    - AI-generated summary answers

    Use this tool when you need to find current information from the web,
    research topics, or gather data from specific sources.
    """

    name = "tavily_search"
    input_schema = TavilySearchInput
    description = (
        "Search the web using Tavily API. "
        "Takes a list of search queries and returns relevant web results. "
        "Supports multiple queries, domain filtering, and configurable search depth. "
        "Use this tool to find current information, research topics, or gather data from the web. "
        "Each query is searched independently and results are combined."
    )

    def __init__(self) -> None:
        """Initialize TavilySearchTool."""
        if not settings.TAVILY_API_KEY:
            logger.warning(
                "TAVILY_API_KEY not set in environment. Tool will not function properly."
            )

    async def _search_single_query(
        self,
        client: AsyncTavilyClient,
        query: str,
        max_results: int,
        search_depth: Literal["basic", "advanced"],
        include_domains: list[str] | None,
        exclude_domains: list[str] | None,
        include_answer: bool,
        include_raw_content: bool,
    ) -> dict[str, Any]:
        """Execute a single search query.

        Args:
            client: Tavily async client instance
            query: Search query string
            max_results: Maximum number of results
            search_depth: Search depth ('basic' or 'advanced')
            include_domains: Domains to include
            exclude_domains: Domains to exclude
            include_answer: Whether to include AI summary
            include_raw_content: Whether to include raw content

        Returns:
            Dictionary containing query and search results
        """
        try:
            logger.info("Executing Tavily search for query: %s", query)

            response = await client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                include_answer=include_answer,
                include_raw_content=include_raw_content,
            )

            logger.debug(
                "Tavily search completed for query '%s': %d results",
                query,
                len(response.get("results", [])),
            )

            return {
                "query": query,
                "answer": response.get("answer"),
                "results": response.get("results", []),
                "follow_up_questions": response.get("follow_up_questions"),
            }

        except Exception as e:
            logger.warning("Failed to execute search for query '%s': %s", query, str(e))
            return {
                "query": query,
                "error": str(e),
                "results": [],
            }

    async def arun(
        self,
        queries: list[str],
        max_results: int = 5,
        search_depth: str = "basic",
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        include_answer: bool = True,
        include_raw_content: bool = False,
    ) -> ToolOutput:
        """Search the web with multiple queries.

        Args:
            queries: List of search queries to execute
            max_results: Maximum number of results per query (1-20, default: 5)
            search_depth: Search depth - 'basic' or 'advanced' (default: basic)
            include_domains: Optional list of domains to include
            exclude_domains: Optional list of domains to exclude
            include_answer: Whether to include AI-generated summary (default: true)
            include_raw_content: Whether to include raw page content (default: false)

        Returns:
            ToolOutput with JSON containing search results for all queries
        """
        try:
            # Check if API key is configured
            if not settings.TAVILY_API_KEY:
                error_data = {
                    "error": "configuration_error",
                    "message": "Web search is not available. The search service requires configuration. Please contact your administrator.",
                    "queries": queries,
                }
                return ToolOutput(type="error-json", value=error_data)

            logger.info(
                "Starting Tavily search for %d queries with depth: %s",
                len(queries),
                search_depth,
            )

            # Initialize Tavily client
            client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)

            # Execute all searches in parallel
            tasks = [
                self._search_single_query(
                    client=client,
                    query=query,
                    max_results=max_results,
                    search_depth=search_depth,
                    include_domains=include_domains,
                    exclude_domains=exclude_domains,
                    include_answer=include_answer,
                    include_raw_content=include_raw_content,
                )
                for query in queries
            ]

            results = await asyncio.gather(*tasks)

            # Prepare response
            response_data = {
                "queries": queries,
                "search_depth": search_depth,
                "max_results_per_query": max_results,
                "total_queries": len(queries),
                "results": results,
            }

            # Count total results and errors
            total_results = sum(len(r.get("results", [])) for r in results)
            total_errors = sum(1 for r in results if "error" in r)

            logger.info(
                "TavilySearchTool completed: %d queries, %d total results, %d errors",
                len(queries),
                total_results,
                total_errors,
            )

            return ToolOutput(type="json", value=response_data)

        except Exception as e:
            logger.exception("TavilySearchTool failed: %s", str(e))
            error_data = {
                "error": "tavily_search_error",
                "message": f"Unable to complete web search. Please try again or rephrase your query. Error: {e!s}",
                "queries": queries,
            }
            return ToolOutput(type="error-json", value=error_data)
