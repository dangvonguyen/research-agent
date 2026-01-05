"""Research Search Tool - implements comprehensive web search workflow for research questions."""

import asyncio
import json
import logging
import re
from typing import Any, Literal

from llama_index.core.llms import ChatMessage, MessageRole
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.ai.tools.tavily_search import TavilySearchTool
from app.services.llm_service import llm_service
from app.types import ToolResultOutput as ToolOutput

logger = logging.getLogger(__name__)


class ResearchSearchInput(BaseModel):
    """Input schema for ResearchSearchTool."""

    queries: list[str] = Field(
        description="List of search queries to execute. Each query will be searched independently and results will be combined."
    )
    question: str = Field(
        description="Research question to guide document selection and relevance filtering"
    )
    max_results: int = Field(
        default=20,
        description="Maximum number of results to return per query (default: 20)",
        ge=1,
        le=50,
    )
    search_depth: Literal["basic", "advanced"] = Field(
        default="advanced",
        description="Search depth: 'basic' for quick results or 'advanced' for comprehensive search (default: advanced)",
    )
    include_domains: list[str] | None = Field(
        default=None,
        description="Optional list of domains to specifically include in the search. Defaults to ['https://aclanthology.org'] if not provided.",
    )
    exclude_domains: list[str] | None = Field(
        default=None,
        description="Optional list of domains to exclude from the search (e.g., ['wikipedia.org'])",
    )
    k: int = Field(
        default=10,
        description="Number of most relevant documents to select for answering the question (default: 10)",
        ge=1,
        le=20,
    )
    max_chars_per_doc: int = Field(
        default=1000,
        description="Maximum characters to extract from each document's raw content (default: 1000)",
        ge=100,
        le=5000,
    )


class ResearchSearchTool(BaseTool):
    """Tool for comprehensive research search.

    This tool implements a complete research workflow:
    1. Search the web using Tavily API with multiple queries (default domain: https://aclanthology.org)
    2. Extract raw content and URLs from search results
    3. Extract evidence (metadata + abstract) from documents
    4. Select most relevant documents using LLM
    5. Return selected documents with their content and URLs

    Use this tool when you need to find relevant documents from the web
    for research questions. The tool returns documents with URLs so the agent
    can reference the source papers in its response.
    """

    name = "research_search"
    input_schema = ResearchSearchInput
    description = (
        "Comprehensive research search tool that searches the web, extracts and selects "
        "relevant documents. "
        "Takes multiple search queries and a research question, then returns the most relevant "
        "documents with their content and URLs. "
        "By default searches in https://aclanthology.org domain. "
        "Use this tool to find relevant documents for research questions that require current information from the web."
    )

    def __init__(self):
        """Initialize ResearchSearchTool."""
        self.tavily_tool = TavilySearchTool()
        self.llm = llm_service.get_default_llm()

    def _extract_raw_contents(
        self, tavily_responses: list[dict[str, Any]], max_chars_per_doc: int
    ) -> list[dict[str, str]]:
        """Extract and truncate raw_content and URL from Tavily responses.

        Args:
            tavily_responses: List of Tavily search response dictionaries
            max_chars_per_doc: Maximum characters per document

        Returns:
            List of dictionaries with 'content' and 'url' keys
        """
        documents = []

        for response in tavily_responses:
            for result in response.get("results", []):
                raw = result.get("raw_content")
                url = result.get("url", "")
                if not raw:
                    continue

                raw = raw.strip()
                if len(raw) > max_chars_per_doc:
                    raw = raw[:max_chars_per_doc]

                documents.append({"content": raw, "url": url})

        return documents

    def _extract_evidence(
        self, text: str, meta_chars: int = 400, abs_chars: int = 600
    ) -> str:
        """Extract evidence from text (metadata + abstract).

        Args:
            text: Raw document text
            meta_chars: Characters to include before 'Abstract'
            abs_chars: Characters to include after 'Abstract'

        Returns:
            Extracted evidence string with metadata and abstract
        """
        match = re.search(r"\babstract\b", text, re.IGNORECASE)

        if not match:
            return text[: meta_chars + abs_chars]

        start_pos = max(0, match.start() - meta_chars)
        end_pos = match.end() + abs_chars

        meta = text[start_pos : match.start()].strip()
        abstract = text[match.end() : end_pos].strip()

        return f"Metadata:\n{meta}\n\nAbstract:\n{abstract}"

    async def _select_relevant_docs(
        self, raw_docs: list[dict[str, str]], question: str, k: int
    ) -> list[dict[str, str]]:
        """Select k most relevant documents using LLM.

        Args:
            raw_docs: List of dictionaries with 'content' and 'url' keys
            question: Research question
            k: Number of documents to select

        Returns:
            List of selected document dictionaries with 'content' and 'url' keys
        """
        if not raw_docs:
            return []

        if len(raw_docs) <= k:
            return raw_docs

        snippets = [self._extract_evidence(doc["content"]) for doc in raw_docs]

        prompt = f"""You are selecting relevant scientific documents.

Research question:
{question}

Select the {k} most relevant documents.

IMPORTANT:
- Return ONLY a JSON array of integers
- No explanation
- Indices must refer to the document numbers below

Documents:
""" + "\n\n".join(f"[{i}] {snippet}" for i, snippet in enumerate(snippets))

        try:
            messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="You are a helpful research assistant.",
                ),
                ChatMessage(role=MessageRole.USER, content=prompt),
            ]

            response = await self.llm.achat(messages)
            response_text = str(response.message.content).strip()

            # Try to extract JSON array from response
            # Handle cases where response might have markdown code blocks
            if "```" in response_text:
                # Extract content between code blocks
                match = re.search(
                    r"```(?:json)?\s*(\[.*?\])\s*```", response_text, re.DOTALL
                )
                if match:
                    response_text = match.group(1)

            # Try to parse as JSON array
            try:
                indices = json.loads(response_text)
                if not isinstance(indices, list):
                    raise ValueError("Response is not a list")

                # Validate indices
                valid_indices = [
                    i for i in indices if isinstance(i, int) and 0 <= i < len(raw_docs)
                ]
                if not valid_indices:
                    logger.warning(
                        "No valid indices found, returning first k documents"
                    )
                    return raw_docs[:k]

                selected_docs = [raw_docs[i] for i in valid_indices[:k]]
                return selected_docs

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    f"Failed to parse LLM response as JSON: {e}. Response: {response_text}"
                )
                # Fallback: try eval (less safe but sometimes works)
                try:
                    indices = eval(response_text.strip())  # noqa: S307
                    if isinstance(indices, list):
                        valid_indices = [
                            i
                            for i in indices
                            if isinstance(i, int) and 0 <= i < len(raw_docs)
                        ]
                        if valid_indices:
                            return [raw_docs[i] for i in valid_indices[:k]]
                except Exception:
                    pass

                # Final fallback: return first k documents
                logger.warning("Using fallback: returning first k documents")
                return raw_docs[:k]

        except Exception as e:
            logger.error(f"Error in _select_relevant_docs: {e}")
            # Fallback: return first k documents
            return raw_docs[:k]

    async def arun(
        self,
        queries: list[str],
        question: str,
        max_results: int = 20,
        search_depth: str = "advanced",
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        k: int = 10,
        max_chars_per_doc: int = 1000,
    ) -> ToolOutput:
        """Execute comprehensive research search workflow.

        Args:
            queries: List of search queries to execute
            question: Research question to guide document selection
            max_results: Maximum number of results per query (default: 20)
            search_depth: Search depth - 'basic' or 'advanced' (default: advanced)
            include_domains: Optional list of domains to include (defaults to ['https://aclanthology.org'])
            exclude_domains: Optional list of domains to exclude
            k: Number of most relevant documents to select (default: 10)
            max_chars_per_doc: Maximum characters per document (default: 1000)

        Returns:
            ToolOutput with JSON containing search results with documents (content and URLs)
        """
        try:
            logger.info(
                f"Starting research search for {len(queries)} queries with question: {question[:100]}"
            )

            # Step 1: Search using Tavily
            # Default to https://aclanthology.org if no domains specified
            search_domains = (
                include_domains
                if include_domains is not None
                else ["https://aclanthology.org"]
            )

            tavily_output = await self.tavily_tool.arun(
                queries=queries,
                max_results=max_results,
                search_depth=search_depth,
                include_domains=search_domains,
                exclude_domains=exclude_domains,
                include_answer=False,
                include_raw_content=True,  # Need raw content for processing
            )

            if tavily_output.type.startswith("error"):
                return ToolOutput(type="error-json", value=tavily_output.value)

            tavily_data = tavily_output.value
            tavily_responses = tavily_data.get("results", [])

            # Step 2: Extract raw contents with URLs
            raw_docs = self._extract_raw_contents(tavily_responses, max_chars_per_doc)
            logger.info(f"Extracted {len(raw_docs)} documents from search results")

            if not raw_docs:
                return ToolOutput(
                    type="error-json",
                    value={
                        "error": "no_results",
                        "message": "No documents found in search results",
                        "queries": queries,
                    },
                )

            # Step 3: Select relevant documents
            relevant_docs = await self._select_relevant_docs(raw_docs, question, k)
            logger.info(f"Selected {len(relevant_docs)} relevant documents")

            # Prepare response with documents and URLs
            response_data = {
                "queries": queries,
                "question": question,
                "total_documents_found": len(raw_docs),
                "documents_selected": len(relevant_docs),
                "documents": [
                    {
                        "content": doc["content"],
                        "url": doc["url"],
                    }
                    for doc in relevant_docs
                ],
                "search_metadata": {
                    "search_depth": search_depth,
                    "max_results_per_query": max_results,
                    "k": k,
                    "include_domains": search_domains,
                },
            }

            logger.info("Research search completed successfully")

            return ToolOutput(type="json", value=response_data)

        except Exception as e:
            logger.exception(f"ResearchSearchTool failed: {str(e)}")
            error_data = {
                "error": "research_search_error",
                "message": f"Unable to complete research search. Error: {e!s}",
                "queries": queries,
                "question": question,
            }
            return ToolOutput(type="error-json", value=error_data)
