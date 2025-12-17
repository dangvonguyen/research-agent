import asyncio
import logging
from pathlib import Path
from typing import Any, Literal

from llama_index.core.llms import ChatMessage, ImageBlock, MessageRole, TextBlock
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.services.llm_service import llm_service
from app.services.zilliz_service import zilliz_service
from app.types import ToolResultOutput as ToolOutput

logger = logging.getLogger(__name__)


class ImageAnalysisInput(BaseModel):
    """Input schema for ImageAnalysisTool."""

    chunk_ids: list[str] = Field(
        description="List of chunk IDs that contain images to analyze"
    )
    question: str | None = Field(
        default=None,
        description="Optional specific question to ask about the images. If not provided, returns general description.",
    )
    analysis_type: Literal["general", "question"] = Field(
        default="general",
        description="Type of analysis: 'general' for description, 'question' for answering specific questions",
    )


class ImageAnalysisTool(BaseTool):
    """Tool for analyzing images from paper sections using vision-capable LLMs.

    This tool:
    1. Retrieves chunks with associated images from the vector store
    2. Loads images from the filesystem
    3. Uses LLMs to analyze images in context
    4. Returns structured analysis results
    """

    name = "analyze_image"
    input_schema = ImageAnalysisInput
    description = (
        "Analyze images from paper sections using vision-capable LLMs. "
        "Takes chunk IDs that contain images and returns detailed analysis. "
        "Supports both general description and question-driven analysis. "
        "Use this to understand figures, diagrams, charts, and visualizations in research papers."
    )

    def __init__(self):
        """Initialize ImageAnalysisTool."""
        self.upload_dir = Path("crawled_papers")
        self.llm_service = llm_service
        self.zilliz_service = zilliz_service

    def _build_prompt(
        self,
        chunk: dict[str, Any],
        question: str | None,
        analysis_type: str,
    ) -> str:
        """Build context-aware prompt for image analysis.

        Args:
            chunk: Chunk metadata including content and section info
            question: Optional specific question about the image
            analysis_type: Type of analysis ("general" or "question")

        Returns:
            Formatted prompt string
        """
        # Get context from surrounding text (first 300 characters)
        context = chunk.get("chunk_content", "")[:300]
        section_name = chunk.get("section_name", "Unknown Section")

        if analysis_type == "question" and question:
            prompt = (
                f"Question: {question}\n\n"
                f"Context from paper section '{section_name}':\n{context}\n\n"
                f"Analyze the image and answer the question based on what you see in the image. "
                f"Relate your answer to the surrounding text context if relevant."
            )
        else:
            prompt = (
                f"Describe this figure from a research paper in detail.\n\n"
                f"Context from paper section '{section_name}':\n{context}\n\n"
                f"Provide a comprehensive description of what the image shows, "
                f"explaining the key elements, patterns, or information presented. "
                f"Relate it to the surrounding text context if relevant."
            )

        return prompt

    async def _get_chunks_with_images(
        self, chunk_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Retrieve chunk metadata for chunks that have associated images.

        Args:
            chunk_ids: List of chunk IDs to query

        Returns:
            List of chunk metadata dictionaries (only chunks with images)
        """
        try:
            # Build filter expression
            filter_expr = f"chunk_id IN {chunk_ids}"

            logger.debug(
                "Querying Zilliz for %d chunks with filter: %s",
                len(chunk_ids),
                filter_expr,
            )

            # Query Zilliz for chunk metadata
            results = self.zilliz_service.query(
                filter=filter_expr,
                limit=len(chunk_ids),
                output_fields=[
                    "chunk_id",
                    "paper_id",
                    "paper_title",
                    "section_name",
                    "chunk_content",
                    "image_path",
                ],
            )

            # Filter to only chunks with valid image paths
            chunks_with_images = [
                r for r in results if r.get("image_path") and r["image_path"].strip()
            ]

            logger.info(
                "Found %d chunks with images out of %d queried",
                len(chunks_with_images),
                len(chunk_ids),
            )

            return chunks_with_images

        except Exception as e:
            logger.exception("Failed to query chunks: %s", str(e))
            return []

    async def _analyze_single_image(
        self,
        chunk: dict[str, Any],
        question: str | None,
        analysis_type: str,
    ) -> dict[str, Any]:
        """Analyze a single image and return structured result.

        Args:
            chunk: Chunk metadata including image_path
            question: Optional specific question
            analysis_type: Type of analysis

        Returns:
            Dictionary with analysis result or error information
        """
        chunk_id = chunk["chunk_id"]

        try:
            # Construct full image path
            image_path = self.upload_dir / chunk["image_path"]

            logger.error("Analyzing image at %s for chunk %s", image_path, chunk_id)

            # Check if image exists
            if not image_path.exists():
                logger.warning("Image not found: %s", image_path)
                return {
                    "status": "error",
                    "chunk_id": chunk_id,
                    "error": "image_not_found",
                    "message": "Image file not found",
                }

            # Build context-aware prompt
            prompt = self._build_prompt(chunk, question, analysis_type)

            # Get default LLM
            llm = self.llm_service.get_default_llm()

            # Create chat message with image
            message = ChatMessage(
                role=MessageRole.USER,
                blocks=[
                    TextBlock(text=prompt),
                    ImageBlock(path=image_path),
                ],
            )

            # Call LLM with vision
            response = await llm.achat([message])
            logger.info("Successfully analyzed image for chunk %s", chunk_id)

            # Extract analysis text
            analysis = response.message.content

            # Return successful result
            return {
                "status": "success",
                "chunk_id": chunk_id,
                "paper_id": chunk["paper_id"],
                "paper_title": chunk["paper_title"],
                "image_path": chunk["image_path"],
                "analysis": analysis,
                "context": {
                    "section_name": chunk["section_name"],
                    "chunk_preview": chunk["chunk_content"][:300],
                },
            }

        except FileNotFoundError as e:
            logger.warning("Image file not found for chunk %s: %s", chunk_id, str(e))
            return {
                "status": "error",
                "chunk_id": chunk_id,
                "error": "image_not_found",
                "message": str(e),
            }

        except Exception as e:
            logger.exception(
                "Failed to analyze image for chunk %s: %s", chunk_id, str(e)
            )
            return {
                "status": "error",
                "chunk_id": chunk_id,
                "error": "analysis_failed",
                "message": "Failed to analyze image",
            }

    async def arun(
        self,
        chunk_ids: list[str],
        question: str | None = None,
        analysis_type: Literal["general", "question"] = "general",
    ) -> ToolOutput:
        """Analyze images from paper chunks using vision-capable LLMs.

        Args:
            chunk_ids: List of chunk IDs that contain images to analyze
            question: Optional specific question to ask about the images
            analysis_type: Type of analysis ("general" or "question")

        Returns:
            ToolOutput with JSON containing analysis results or error information
        """
        try:
            logger.info(
                "Starting image analysis for %d chunks (type: %s)",
                len(chunk_ids),
                analysis_type,
            )

            # Validate input
            if not chunk_ids:
                logger.warning("No chunk IDs provided")
                return ToolOutput(
                    type="error-json",
                    value={
                        "error": "invalid_input",
                        "message": "chunk_ids list cannot be empty",
                        "chunk_ids": chunk_ids,
                    },
                )

            # Step 1: Retrieve chunk metadata from Zilliz
            chunks_with_images = await self._get_chunks_with_images(chunk_ids)

            if not chunks_with_images:
                logger.warning("No images found for the provided chunk IDs")
                return ToolOutput(
                    type="error-json",
                    value={
                        "error": "no_images_found",
                        "message": "No images found for the provided chunk IDs. These chunks may not have associated images.",
                        "chunk_ids": chunk_ids,
                    },
                )

            # Step 2: Analyze each image in parallel
            logger.info("Analyzing %d images in parallel", len(chunks_with_images))

            tasks = [
                self._analyze_single_image(chunk, question, analysis_type)
                for chunk in chunks_with_images
            ]

            analyses = await asyncio.gather(*tasks)

            # Step 3: Separate successful analyses from errors
            successful = [a for a in analyses if a.get("status") == "success"]
            failed = [a for a in analyses if a.get("status") == "error"]

            logger.info(
                "Image analysis completed: %d successful, %d failed",
                len(successful),
                len(failed),
            )

            # Step 4: Format response
            response = {
                "analyses": successful,
                "total_images_analyzed": len(successful),
                "failed_analyses": len(failed),
                "errors": failed if failed else None,
                "question": question,
                "analysis_type": analysis_type,
            }

            return ToolOutput(type="json", value=response)

        except Exception as e:
            logger.exception("ImageAnalysisTool failed: %s", e)
            return ToolOutput(
                type="error-json",
                value={
                    "error": "image_analysis_error",
                    "message": "Failed to analyze images. Please try again.",
                    "details": str(e),
                },
            )
