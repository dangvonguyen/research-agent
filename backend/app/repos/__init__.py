from .base_repo import BaseRepository
from .crawler_repo import CrawlerConfigRepository, CrawlerJobRepository
from .paper_repo import PaperRepository

__all__ = [
    "BaseRepository",
    "CrawlerConfigRepository",
    "CrawlerJobRepository",
    "PaperRepository",
]


async def create_indexes() -> None:
    """
    Create indexes for the database.
    """
    await CrawlerConfigRepository._create_indexes()
    await CrawlerJobRepository._create_indexes()
    await PaperRepository._create_indexes()
