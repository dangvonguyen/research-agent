import asyncio
import logging
import random
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal, Self, cast

import aiofiles
import aiohttp

from app.models import PaperCreate, PaperSource

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Base class that defines the interface for all crawlers."""

    # List of common user agents to rotate
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(
        self,
        source: PaperSource,
        rate_limit: int = 20,
        max_delay: int = 60,
        max_attempts: int = 3,
        max_concurrent: int = 10,
        output_dir: str = "crawled_papers",
    ) -> None:
        """
        Initialize a crawler.
        """
        self.source = source
        self.rate_limit = rate_limit
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self.max_concurrent = max_concurrent
        self.output_dir = Path(output_dir)

        self.delay = 60.0 / self.rate_limit
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Runtime state
        self.session: aiohttp.ClientSession | None = None
        self.semaphore: asyncio.Semaphore | None = None
        self.visited_urls: set[str] = set()
        self._last_request_time: float = 0.0

        config_dict = (dict(locals()))
        config_dict.pop("self")
        logger.debug(
            "Initialized %s with settings: %s",
            self.__class__.__name__,
            ", ".join(f"{k}={v}" for k, v in config_dict.items()),
        )

    async def __aenter__(self) -> Self:
        """
        Enter the crawler context manager.
        """
        await self.init_session()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore
        """
        Exit the crawler context manager.
        """
        await self.close_session()

    async def init_session(self) -> None:
        """
        Initialize an aiohttp session and semaphore.
        """
        logger.debug("Initializing HTTP session")
        self.session = aiohttp.ClientSession()
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        logger.debug("HTTP session initialized")

    async def close_session(self) -> None:
        """
        Close aiohttp session.
        """
        if self.session:
            logger.debug("Closing HTTP session")
            await self.session.close()
            self.session = None
            logger.debug("HTTP session closed")
        else:
            logger.warning("Attempted to close HTTP session that was not initialized")

    async def _backoff(self, attempt: int, reason: str) -> None:
        """
        Backoff for a given attempt.
        """
        # Exponential backoff
        exponential_delay = 2**attempt * self.delay

        # Cap the delay to prevent excessive waiting
        capped_delay = min(exponential_delay, self.max_delay)

        # Add jitter to the delay to prevent thundering herd
        jitter_factor = 0.75 + random.random() * 0.5  # Between 0.75 and 1.25
        final_delay = capped_delay * jitter_factor

        logger.warning(
            "Request failed: %s, backing off for %.2f seconds (attempt %d/%d)",
            reason, final_delay, attempt + 1, self.max_attempts,
        )
        await asyncio.sleep(final_delay)

    async def fetch_with_retry(
        self, url: str, mode: Literal["str", "bytes"] = "str", attempt: int = 0
    ) -> str | bytes | None:
        """
        Fetch a URL with retry and exponential backoff.
        """
        if not self.session or not self.semaphore:
            logger.error("HTTP session not initialized before fetch_with_retry")
            return None

        try:
            # Select a random user agent
            headers = {
                "User-Agent": random.choice(self.USER_AGENTS),
                "Connection": "keep-alive",
                "DNT": "1",  # Do not track
            }

            logger.debug(
                "Fetching URL %s (attempt %d/%d)", url, attempt + 1, self.max_attempts,
            )

            async with self.semaphore:
                # Add delay for rate limiting
                if attempt == 0:
                    elapsed = asyncio.get_event_loop().time() - self._last_request_time
                    if elapsed < self.delay:
                        await asyncio.sleep(self.delay - elapsed)

                self._last_request_time = asyncio.get_event_loop().time()

                async with self.session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        content: str | bytes | None = None
                        if mode == "str":
                            content = await resp.text()
                        else:
                            content = await resp.read()

                        logger.debug("Successfully fetched URL %s", url)
                        return content

                    logger.warning(
                        "HTTP error %d for URL %s (attempt %d/%d)",
                        resp.status, url, attempt + 1, self.max_attempts,
                    )

                    # Check if we should retry
                    if resp.status >= 500 or resp.status == 429:
                        pass
                    else:
                        logger.debug(
                            "Client error %d for URL %s - not retrying",
                            resp.status, url,
                        )
                        return None

            if attempt < self.max_attempts - 1:
                await self._backoff(attempt, f"HTTP error {resp.status}")
                return await self.fetch_with_retry(url, mode, attempt + 1)
            else:
                logger.error("Max attempts reached for URL %s", url)
                return None

        except asyncio.TimeoutError:  # noqa: UP041
            logger.warning(
                "Timeout fetching URL %s (attempt %d/%d): %s",
                url, attempt + 1, self.max_attempts,
            )
            if attempt < self.max_attempts - 1:
                await self._backoff(attempt, "timeout")
                return await self.fetch_with_retry(url, mode, attempt + 1)
            return None

        except Exception as e:
            logger.exception(
                "Unexpected error fetching URL %s (attempt %d/%d): %s",
                url, attempt + 1, self.max_attempts, str(e),
            )
            if attempt < self.max_attempts - 1:
                await self._backoff(attempt, f"unexpected error: {e}")
                return await self.fetch_with_retry(url, mode, attempt + 1)
            return None

    async def fetch_url(
        self, url: str, mode: Literal["str", "bytes"] = "str"
    ) -> str | bytes | None:
        """
        Fetch a URL with rate limiting and concurrency control.
        """
        # Check if we already visited this URL
        if url in self.visited_urls:
            logger.debug("Skipping already visited URL %s", url)
            return None

        # Mark as visited
        self.visited_urls.add(url)

        # Fetch with retry
        logger.debug("Fetching URL %s", url)
        content = await self.fetch_with_retry(url, mode)

        if content:
            logger.debug("Fetch completed for URL %s", url)
        else:
            logger.warning("Failed to fetch URL %s after all retries", url)

        return content

    async def download_pdf(self, paper: PaperCreate) -> None:
        """
        Download a paper's PDF.
        """
        if not paper.pdf_url or not paper.local_pdf_path:
            logger.warning("No PDF URL available for paper '%s'", paper.source_id)
            return

        # Get filepath for the PDF
        filepath = Path(paper.local_pdf_path)

        # Skip if already downloaded
        if filepath.exists():
            logger.debug("PDF already exists for paper '%s': %s", paper.source_id, filepath)
            return

        logger.debug("Downloading PDF for paper '%s'", paper.source_id)
        pdf_content = cast(bytes | None, await self.fetch_url(paper.pdf_url, "bytes"))

        if not pdf_content:
            logger.warning("Failed to download PDF for paper '%s'", paper.source_id)
            return

        try:
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(pdf_content)

            logger.info(
                "Successfully downloaded PDF for paper '%s' to %s",
                paper.source_id, filepath,
            )
        except Exception as e:
            logger.error("Error saving PDF for paper '%s': %s", paper.source_id, str(e))

    @abstractmethod
    async def crawl(
        self,
        query: str | None = None,
        urls: list[str] | None = None,
        max_papers: int | None = None,
    ) -> list[PaperCreate]:
        """
        Crawl the specified URLs and/or query and extract paper information.
        """
        pass
