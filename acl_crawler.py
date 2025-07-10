import os
import json
import asyncio
from dataclasses import dataclass, asdict, field

import aiohttp
from bs4 import BeautifulSoup


@dataclass
class Paper:
    id: str
    title: str
    authors: list[str]
    anthology_url: str
    pdf_url: str | None = None
    abstract: str | None = None
    year: int | None = None
    venues: list[str] = field(default_factory=list)


class ACLAnthologyCrawler:
    """A crawler for the ACL Anthology website."""

    BASE_URL = "https://aclanthology.org"

    def __init__(self, output_dir: str, max_concurrent: int = 5, delay: float = 0.5):
        self.output_dir = output_dir
        self.max_concurrent = max_concurrent
        self.delay = delay
        self.visited_urls: set[str] = set()
        self.session: aiohttp.ClientSession | None = None
        self.semaphore: asyncio.Semaphore | None = None

        self.metadata_filepath = os.path.join(self.output_dir, "metadata.jsonl")

    async def init_session(self):
        """Initialize aiohttp session and semaphore for concurrent downloads."""
        self.session = aiohttp.ClientSession()
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

    async def close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()

    def parse_acl_url(self, url: str) -> tuple[str, str | None]:
        """Parse ACL URL to extract base URL and conference ID."""
        if "#" in url:
            base_url, conf_id = url.split("#", 1)
            return base_url, conf_id
        else:
            return url, None

    async def fetch_page(self, url: str) -> str | None:
        """Fetch a web page with rate limiting."""
        if url in self.visited_urls:
            return None

        self.visited_urls.add(url)

        try:
            assert self.session is not None
            assert self.semaphore is not None

            async with self.semaphore:
                await asyncio.sleep(self.delay)
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    else:
                        print(f"Failed to fetch {url}, status: {resp.status}")
                        return None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    async def download_pdf(self, paper: Paper) -> None:
        """Download a paper's PDF."""
        os.makedirs(self.output_dir, exist_ok=True)

        filename = f"{paper.id}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        # Skip if already downloaded
        if os.path.exists(filepath):
            return

        try:
            pdf_url = paper.pdf_url
            if not pdf_url:
                print(f"No PDF URL for {paper.id}")
                return

            assert self.session is not None
            assert self.semaphore is not None

            async with self.semaphore:
                await asyncio.sleep(self.delay)
                async with self.session.get(pdf_url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(filepath, "wb") as f:
                            f.write(content)
                        with open(self.metadata_filepath, "a", encoding="utf-8") as f:
                            f.write(json.dumps(asdict(paper), indent=2) + "\n")
                    else:
                        print(f"Failed to download {pdf_url}, status: {resp.status}")
        except Exception as e:
            print(f"Error downloading {pdf_url}: {e}")

    async def fetch_paper_metadata(self, paper_id: str) -> Paper | None:
        """Extract paper metadata from a paper HTML element."""
        anthology_url = f"{self.BASE_URL}/{paper_id}"

        html_content = await self.fetch_page(anthology_url)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, "html.parser")

        try:
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

            return Paper(
                id=paper_id,
                title=title,
                authors=authors,
                anthology_url=anthology_url,
                abstract=abstract,
                pdf_url=pdf_url,
                year=year,
                venues=venues,
            )
        except Exception as e:
            print(f"Error fetching paper metadata: {e}, {paper_id}")
            return None


    async def process_paper(self, paper_id: str) -> None:
        """Process a single paper element: extract metadata, fetch abstract, download PDF."""
        paper = await self.fetch_paper_metadata(paper_id)
        if not paper:
            return

        await self.download_pdf(paper)

    async def process_single_paper(self, url: str) -> None:
        """Process a single paper element with a direct URL."""
        paper_id = [part for part in url.split("/") if part][-1]
        await self.process_paper(paper_id)

    async def process_query_page(self, url: str) -> None:
        """Process a query page and extract papers."""
        # TODO: Implement query page processing
        pass

    async def process_conference_page(self, url: str) -> None:
        """Process a conference page and extract papers."""
        base_url, conf_id = self.parse_acl_url(url)

        html_content = await self.fetch_page(base_url)
        if not html_content:
            return

        soup = BeautifulSoup(html_content, "html.parser")

        if conf_id:
            section = soup.find(id=conf_id)
            if section:
                papers = section.find_all("p", class_="d-sm-flex")  # type: ignore
            else:
                papers = []
        else:
            papers = soup.find_all("p", class_="d-sm-flex")

        tasks = []
        for paper_element in papers:
            paper_id = (
                paper_element.find(class_="badge")["href"]  # type: ignore
                .rsplit("/", maxsplit=1)[-1]
                .rsplit(".", maxsplit=1)[0]
            )
            tasks.append(self.process_paper(paper_id))

        await asyncio.gather(*tasks)

    async def crawl(self, urls: list[str]) -> None:
        """Main crawling method."""
        await self.init_session()

        try:
            tasks = []
            for url in urls:
                if "/events/" in url:
                    tasks.append(self.process_conference_page(url))
                elif "/search/" in url:
                    tasks.append(self.process_query_page(url))
                else:
                    tasks.append(self.process_single_paper(url))

            await asyncio.gather(*tasks)
        finally:
            await self.close_session()


async def main():
    output_dir = "acl_papers"
    max_concurrent = 5
    delay = 0.5
    example_urls = [
        "https://aclanthology.org/events/acl-2024/#2024knowledgenlp-1",
        "https://aclanthology.org/2024.acl-long.1/"
    ]

    crawler = ACLAnthologyCrawler(output_dir, max_concurrent, delay)

    await crawler.crawl(urls=example_urls)


if __name__ == "__main__":
    asyncio.run(main())
