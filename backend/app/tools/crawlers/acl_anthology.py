import asyncio
import logging
from typing import Any, cast

from bs4 import BeautifulSoup

from app.models import PaperCreate, PaperSource
from app.utils import bulk_run

from .base import BaseCrawler

logger = logging.getLogger(__name__)


class ACLAnthologyCrawler(BaseCrawler):
    """Crawler for the ACL Anthology website."""

    BASE_URL = "https://aclanthology.org"

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize the ACL Anthology crawler.
        """
        super().__init__(**kwargs)

        self.parser = ACLAnthologyParser()

        logger.debug("Initialized ACL Anthology crawler")

    async def extract_paper_metadata(self, paper_id: str) -> PaperCreate | None:
        """
        Extract paper metadata from a paper page.
        """
        paper_url = f"{self.BASE_URL}/{paper_id}"
        logger.debug("Extracting metadata for paper %s", paper_id)

        html_content = cast(str | None, await self.fetch_url(paper_url))
        if not html_content:
            logger.warning("Failed to fetch paper page for %s", paper_id)
            return None

        paper = self.parser.parse_paper_page(html_content, paper_id)
        if paper:
            paper.url = paper_url
            if paper.pdf_url:
                paper.local_pdf_path = str(self.output_dir / f"{paper_id}.pdf")
            logger.debug("Successfully extracted metadata for paper: %s", paper.title)
        else:
            logger.warning("Failed to parse paper page for %s", paper_id)
        return paper

    async def process_paper_page(self, url: str) -> PaperCreate | None:
        """
        Process a single paper: extract metadata and prepare for download.
        """
        logger.debug("Processing paper page: %s", url)
        paper_id = [part for part in url.split("/") if part][-1]
        logger.debug("Extracted paper ID: %s", paper_id)

        paper = await self.extract_paper_metadata(paper_id)
        if paper:
            logger.debug("Successfully processed paper: %s", paper.title)
        else:
            logger.warning("Failed to process paper page: %s", url)
        return paper

    async def process_conference_page(self, url: str) -> list[PaperCreate]:
        """
        Process a conference page and extract papers.
        """
        logger.debug("Processing conference page: %s", url)

        base_url, conf_id = self.parser.parse_acl_url(url)

        html_content = cast(str | None, await self.fetch_url(base_url))
        if not html_content:
            logger.warning("Failed to fetch conference page: %s", base_url)
            return []

        if conf_id:
            logger.debug("Parsing paper IDs from conference page in %s", conf_id)
        else:
            logger.debug("Parsing all paper IDs from conference page")
        paper_ids = self.parser.parse_conference_page(html_content, conf_id)

        if paper_ids:
            logger.info("Found %d papers from %s", len(paper_ids), url)
        else:
            logger.warning("No papers found from %s", url)
            return []

        logger.debug("Extracting metadata for %d papers", len(paper_ids))
        results = await bulk_run(self.extract_paper_metadata, paper_ids)

        papers = [r for r in results if r]

        logger.info(
            "Successfully extracted metadata for %d/%d papers from %s",
            len(papers), len(paper_ids), url,
        )
        return papers

    async def process_search_page(self, url: str) -> list[PaperCreate]:
        """
        Process a search query page and extract papers.
        """
        logger.debug("Processing search page: %s", url)

        html_content = cast(str | None, await self.fetch_url(url))
        if not html_content:
            logger.warning("Failed to fetch search page: %s", url)
            return []

        logger.debug("Parsing paper IDs from search page")
        paper_ids = self.parser.parse_search_page(html_content)

        if paper_ids:
            logger.info("Found %d papers from %s", len(paper_ids), url)
        else:
            logger.warning("No papers found from %s", url)
            return []

        logger.debug("Extracting metadata for %d papers", len(paper_ids))
        results = await bulk_run(self.extract_paper_metadata, paper_ids)

        papers = [r for r in results if r]

        logger.info(
            "Successfully extracted metadata for %d/%d papers from %s",
            len(papers), len(paper_ids), url,
        )
        return papers

    async def crawl(self, urls: list[str]) -> list[PaperCreate]:
        """
        Crawl a list of ACL Anthology URLs and extract paper information.
        """
        logger.debug("Starting crawl of %d URLs", len(urls))

        papers: list[PaperCreate] = []

        # Process URLs in parallel
        tasks: list[Any] = []

        for url in urls:
            logger.debug("Processing URL: %s", url)

            if "/events/" in url or "/volumes/" in url:
                # Conference page
                logger.debug("URL %s identified as conference page", url)
                tasks.append(self.process_conference_page(url))
            elif "/search/" in url:
                # Search page
                logger.debug("URL %s identified as search page", url)
                tasks.append(self.process_search_page(url))
            else:
                # Assume paper page
                logger.debug("URL %s identified as paper page", url)
                tasks.append(self.process_paper_page(url))

        # Gather results
        logger.debug("Waiting for all URL processing tasks to complete...")
        results = await asyncio.gather(*tasks)

        # Combine results
        for result in results:
            if isinstance(result, list):
                papers.extend(result)
            elif result is not None:
                papers.append(result)

        logger.info("Crawling completed, found %d papers", len(papers))
        return papers


class ACLAnthologyParser:
    """Parser for ACL Anthology HTML content."""

    @staticmethod
    def parse_paper_page(html_content: str, paper_id: str) -> PaperCreate | None:
        """
        Parse a paper page and extract metadata.
        """
        logger.debug("Parsing paper page for ID: %s", paper_id)

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract metadata
            title_meta = soup.find("meta", attrs={"name": "citation_title"})
            title = title_meta["content"]  # type: ignore
            logger.debug("Found title for paper %s: %s", paper_id, title)

            authors_meta = soup.find_all("meta", attrs={"name": "citation_author"})
            authors = [str(tag["content"]) for tag in authors_meta]  # type: ignore
            logger.debug("Found %d authors for paper %s", len(authors), paper_id)

            # Extract abstract
            abstract_tag = soup.select_one(".acl-abstract > span")
            abstract = abstract_tag.get_text(strip=True) if abstract_tag else None
            if abstract:
                logger.debug("Found abstract for paper %s: %s", paper_id, abstract)
            else:
                logger.debug("No abstract found for paper %s", paper_id)

            # Extract additional metadata
            def get_metadata(tag_string: str) -> str | None:
                tag = soup.find("dt", string=tag_string)
                if tag and tag.find_next_sibling("dd"):
                    return tag.find_next_sibling("dd").get_text(strip=True)  # type: ignore
                return None

            # Extract PDF URL
            pdf_url = get_metadata("PDF:")
            if pdf_url:
                logger.debug("Found PDF URL for paper %s: %s", paper_id, pdf_url)
            else:
                logger.debug("No PDF URL found for paper %s", paper_id)

            # Extract year
            year_str = get_metadata("Year:")
            year = None
            if year_str:
                try:
                    year = int(year_str)
                    logger.debug("Found year for paper %s: %d", paper_id, year)
                except ValueError:
                    logger.warning("Invalid year format for paper %s", paper_id)
            else:
                logger.debug("No year found for paper %s", paper_id)

            # Extract venue
            venue = get_metadata("Venue:") or get_metadata("Venues:")
            venues = venue.split("|") if venue else []
            logger.debug("Found venues for paper %s: %s", paper_id, venues)

            paper = PaperCreate(
                title=title,
                authors=authors,
                source=PaperSource.ACL_ANTHOLOGY,
                source_id=paper_id,
                abstract=abstract,
                year=year,
                pdf_url=pdf_url,
                venues=venues,
            )

            logger.debug("Successfully parsed paper %s", paper_id)
            return paper

        except Exception as e:
            logger.exception("Error parsing paper page %s: %s", paper_id, str(e))
            return None

    @staticmethod
    def parse_conference_page(
        html_content: str, conf_id: str | None = None
    ) -> list[str]:
        """
        Parse a conference page and extract paper IDs.
        """
        logger.debug("Parsing conference page for ID: %s", conf_id)

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            if conf_id:
                section = soup.find(id=conf_id)
                if section:
                    papers = section.find_all("p", class_="d-sm-flex")  # type: ignore
                else:
                    papers = []
            else:
                papers = soup.find_all("p", class_="d-sm-flex")

            paper_ids = []
            for paper_element in papers:
                paper_id = (
                    paper_element.find(class_="badge")["href"]
                    .rsplit("/", maxsplit=1)[-1]
                    .rsplit(".", maxsplit=1)[0]
                )
                paper_ids.append(paper_id)

            logger.debug("Found %d paper IDs in conference page", len(paper_ids))
            return paper_ids

        except Exception as e:
            logger.error("Error parsing conference page: %s", str(e))
            return []

    @staticmethod
    def parse_search_page(html_content: str) -> list[str]:
        """
        Parse a search results page and extract paper IDs.
        """
        # TODO: Implement search page parsing
        return []

    @staticmethod
    def parse_acl_url(url: str) -> tuple[str, str | None]:
        """
        Parse ACL URL to extract base URL and conference ID.
        """
        if "#" in url:
            base_url, conf_id = url.split("#", 1)
            return base_url, conf_id
        else:
            return url, None
