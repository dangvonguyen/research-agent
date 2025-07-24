import asyncio
import logging

import aiofiles
from bs4 import BeautifulSoup

from app.models import PaperCreate, PaperSource

from .base import BaseCrawler

logger = logging.getLogger(__name__)


class ACLAnthologyCrawler(BaseCrawler):
    """Crawler for the ACL Anthology website."""

    BASE_URL = "https://aclanthology.org"

    def __init__(self, **kwargs) -> None:
        """
        Initialize the ACL Anthology crawler.
        """
        super().__init__(**kwargs)

        self.parser = ACLAnthologyParser()

    async def extract_paper_metadata(self, paper_id: str) -> PaperCreate | None:
        """
        Extract paper metadata from a paper page.
        """
        paper_url = f"{self.BASE_URL}/{paper_id}"

        html_content = await self.fetch_url(paper_url)
        if not html_content:
            return None

        paper = self.parser.parse_paper_page(html_content, paper_id)
        if paper:
            paper.url = paper_url
        return paper

    async def process_paper_page(self, url: str) -> PaperCreate | None:
        """
        Process a single paper: extract metadata and prepare for download.
        """
        paper_id = [part for part in url.split("/") if part][-1]

        return await self.extract_paper_metadata(paper_id)

    async def process_conference_page(self, url: str) -> list[PaperCreate]:
        """
        Process a conference page and extract papers.
        """
        base_url, conf_id = self.parser.parse_acl_url(url)

        html_content = await self.fetch_url(base_url)
        if not html_content:
            return []

        paper_ids = self.parser.parse_conference_page(html_content, conf_id)

        tasks = [self.extract_paper_metadata(paper_id) for paper_id in paper_ids]

        return [r for r in await asyncio.gather(*tasks) if r]

    async def process_search_page(self, url: str) -> list[PaperCreate]:
        """
        Process a search query page and extract papers.
        """
        html_content = await self.fetch_url(url)
        if not html_content:
            return []

        paper_ids = self.parser.parse_search_page(html_content)

        tasks = [self.extract_paper_metadata(paper_id) for paper_id in paper_ids]

        return [r for r in await asyncio.gather(*tasks) if r]

    async def download_pdf(self, paper: PaperCreate) -> None:
        """
        Download a paper's PDF.
        """
        if not paper.pdf_url:
            return

        filename = f"{paper.source_id}.pdf"
        filepath = self.output_dir / filename

        # Skip if already downloaded
        if filepath.exists():
            logger.info(f"PaperCreate {paper.source_id} already downloaded")
            return

        try:
            assert self.session is not None
            assert self.semaphore is not None

            async with self.semaphore:
                await asyncio.sleep(self.delay)
                async with self.session.get(paper.pdf_url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        async with aiofiles.open(filepath, "wb") as f:
                            await f.write(content)
                        paper.local_pdf_path = str(filepath)
                        logger.info(f"Downloaded PDF for {paper.source_id}")
                    else:
                        logger.warning(
                            f"Failed to download {paper.pdf_url},status: {resp.status}"
                        )
        except Exception as e:
            logger.error(f"Error downloading PDF {paper.pdf_url}: {e}")

    async def crawl(self, urls: list[str]) -> list[PaperCreate]:
        """
        Crawl the specified URLs and extract paper information.
        """
        await self.init_session()

        try:
            all_papers = []

            for url in urls:
                logger.info(f"Processing URL: {url}")
                try:
                    if "/events/" in url:
                        papers = await self.process_conference_page(url)
                    elif "/search/" in url:
                        papers = await self.process_search_page(url)
                    else:
                        paper = await self.process_paper_page(url)
                        papers = [paper] if paper else []

                    all_papers.extend(papers)

                    for paper in papers:
                        await self.download_pdf(paper)

                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}")

            return all_papers

        except Exception as e:
            logger.error(f"Error during crawl: {e}")
            return []
        finally:
            await self.close_session()


class ACLAnthologyParser:
    """Parser for ACL Anthology HTML content."""

    @staticmethod
    def parse_paper_page(html_content: str, paper_id: str) -> PaperCreate | None:
        """
        Parse a paper page and extract metadata.
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract metadata
            title_meta = soup.find("meta", attrs={"name": "citation_title"})
            title = title_meta["content"]  # type: ignore

            authors_meta = soup.find_all("meta", attrs={"name": "citation_author"})
            authors = [str(tag["content"]) for tag in authors_meta]  # type: ignore

            # Extract abstract
            abstract_tag = soup.select_one(".acl-abstract > span")
            abstract = abstract_tag.get_text(strip=True) if abstract_tag else None

            # Extract additional metadata
            def get_metadata(tag_string: str) -> str | None:
                tag = soup.find("dt", string=tag_string)
                if tag and tag.find_next_sibling("dd"):
                    return tag.find_next_sibling("dd").get_text(strip=True)  # type: ignore
                return None

            pdf_url = get_metadata("PDF:")
            year_str = get_metadata("Year:")
            year = int(year_str) if year_str and year_str.isdigit() else None
            venue = get_metadata("Venue:") or get_metadata("Venues:")
            venues = venue.split("|") if venue else []

            return PaperCreate(
                title=title,
                authors=authors,
                source=PaperSource.ACL_ANTHOLOGY,
                source_id=paper_id,
                abstract=abstract,
                year=year,
                pdf_url=pdf_url,
                venues=venues,
            )

        except Exception as e:
            logger.error(f"Error parsing paper page: {e}")
            return None

    @staticmethod
    def parse_conference_page(
        html_content: str, conf_id: str | None = None
    ) -> list[str]:
        """
        Parse a conference page and extract paper IDs.
        """
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

            return paper_ids

        except Exception as e:
            logger.error(f"Error parsing conference page: {e}")
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
