import asyncio
import logging
import random
from abc import ABC, abstractmethod
from pathlib import Path

import aiohttp

from app.models import Paper, PaperSource

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

    async def init_session(self) -> None:
        """
        Initialize an aiohttp session and semaphore.
        """
        self.session = aiohttp.ClientSession()
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

    async def close_session(self) -> None:
        """
        Close aiohttp session.
        """
        if self.session:
            await self.session.close()
            self.session = None

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

        logger.warning(f"{reason}, backoff for {final_delay:.2f}s")
        await asyncio.sleep(final_delay)

    async def fetch_with_retry(self, url: str, attempt: int = 0) -> str | None:
        """
        Fetch a URL with retry and exponential backoff.
        """
        if attempt >= self.max_attempts:
            logger.warning(f"Max attempts reached for {url}")
            return None

        # Get headers with random user agent
        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Connection": "keep-alive",
            "DNT": "1",  # Do not track
        }

        try:
            assert self.session is not None
            await asyncio.sleep(self.delay)

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"Successfully fetched {url}")
                    return await response.text()
                elif response.status in (429, 403, 503):  # Rate limited or blocked
                    await self._backoff(attempt, f"Rate limited for {url}")
                    return await self.fetch_with_retry(url, attempt + 1)
                else:
                    logger.warning(f"Failed to fetch {url}, status: {response.status}")
                    return None

        except TimeoutError:
            await self._backoff(attempt, f"Timeout for {url}")
            return await self.fetch_with_retry(url, attempt + 1)

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            if attempt < self.max_attempts:
                await self._backoff(attempt, f"Retrying {url}")
            return await self.fetch_with_retry(url, attempt + 1)

    async def fetch_url(self, url: str) -> str | None:
        """
        Fetch a URL with rate limiting and concurrency control.
        """
        if url in self.visited_urls:
            return None

        self.visited_urls.add(url)

        assert self.semaphore is not None
        async with self.semaphore:
            return await self.fetch_with_retry(url)

    @abstractmethod
    async def crawl(self, urls: list[str]) -> list[Paper]:
        """
        Crawl the specified URLs and extract paper information.
        """
        pass

    @abstractmethod
    async def download_pdf(self, paper: Paper) -> None:
        """
        Download a paper's PDF.
        """
        pass

    async def download_all_pdfs(self, papers: list[Paper]) -> None:
        """
        Download all PDFs for a list of papers.
        """
        tasks = [self.download_pdf(paper) for paper in papers]
        await asyncio.gather(*tasks)
