"""Module for handling PDF to Markdown conversion via datalab API."""

import logging
import time
from pathlib import Path
from typing import Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class APIConverter:
    """Handles PDF to Markdown conversion using datalab API."""

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize API converter.

        Args:
            api_key: Datalab API key (defaults to settings)
            api_url: Datalab API URL (defaults to settings)
        """
        self.api_key = api_key or settings.DATALAB_API_KEY
        self.api_url = api_url or settings.DATALAB_API_URL

    def convert_pdf_to_markdown(
        self, pdf_path: str, max_pages: Optional[int] = None
    ) -> dict:
        """
        Convert PDF to markdown using datalab API.

        Args:
            pdf_path: Path to the PDF file
            max_pages: Maximum number of pages to process

        Returns:
            Dictionary with keys:
                - markdown: Markdown content as string
                - images: Dict mapping image names to base64-encoded image data
                - metadata: Dict with metadata
                - status: Status string
                - success: Boolean
                - error: Error message if any
                - page_count: Number of pages
        """
        logger.debug("Uploading PDF to datalab API: %s", pdf_path)

        # Step 1: Upload PDF and request conversion
        with open(pdf_path, "rb") as f:
            files = {"file": (Path(pdf_path).name, f, "application/pdf")}

            payload = {
                "output_format": "markdown",
                "mode": "fast",
                "force_ocr": "false",
                "use_llm": "false",
            }

            if max_pages:
                payload["max_pages"] = str(max_pages)

            headers = {"X-API-Key": self.api_key}

            response = requests.post(
                self.api_url, headers=headers, data=payload, files=files
            )

        if response.status_code != 200:
            raise Exception(
                f"Error uploading PDF: {response.status_code} - {response.text}"
            )

        result = response.json()

        if not result.get("success"):
            raise Exception(
                f"API returned error: {result.get('error', 'Unknown error')}"
            )

        request_id = result.get("request_id")
        request_check_url = result.get("request_check_url")

        if not request_check_url:
            raise Exception("No request_check_url in response")

        logger.debug("Upload successful. Request ID: %s", request_id)

        # Step 2: Poll for completion
        max_attempts = 120  # Maximum 10 minutes (120 * 5 seconds)
        attempt = 0

        while attempt < max_attempts:
            check_response = requests.get(request_check_url, headers=headers)

            if check_response.status_code != 200:
                raise Exception(
                    f"Error checking status: {check_response.status_code} - {check_response.text}"
                )

            result = check_response.json()
            status = result.get("status")

            if status == "complete":
                logger.debug("Conversion completed!")
                break

            if status == "failed":
                error_msg = result.get("error", "Unknown error")
                raise Exception(f"Conversion failed: {error_msg}")
            else:
                attempt += 1
                if attempt % 6 == 0:  # Log every 30 seconds
                    logger.debug(
                        "Still processing... (attempt %d/%d)", attempt, max_attempts
                    )
                time.sleep(5)
        else:
            raise Exception("Conversion timeout - exceeded maximum wait time")

        # Step 3: Extract markdown
        markdown_content = None

        if "markdown" in result:
            markdown_content = result["markdown"]

        if not markdown_content:
            raise Exception("No markdown content found in result")

        logger.debug("Received markdown (%d characters)", len(markdown_content))

        # Extract images from result
        images = result.get("images", {})
        metadata = result.get("metadata", {})
        page_count = result.get("page_count", 0)

        return {
            "markdown": markdown_content,
            "images": images,
            "metadata": metadata,
            "status": result.get("status", "complete"),
            "success": result.get("success", True),
            "error": result.get("error", ""),
            "page_count": page_count,
        }
