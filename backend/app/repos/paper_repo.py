import logging

from pymongo import IndexModel

from app.models import Paper, PaperCreate, PaperSource, PaperUpdate

from .base_repo import BaseRepository

logger = logging.getLogger(__name__)


class PaperRepository(BaseRepository[Paper, PaperCreate, PaperUpdate]):
    """Repository for paper data access."""

    collection_name = "papers"
    model_class = Paper
    indexes = [
        IndexModel([("job_id", 1)], name="paper_job_id"),
        IndexModel([("source", 1)], name="paper_source"),
        IndexModel([("source_id", 1)], name="paper_source_id"),
    ]

    @classmethod
    async def get_by_job_id(
        cls, job_id: str, skip: int = 0, limit: int = 100
    ) -> list[Paper]:
        """
        Get documents with pagination and job ID filter.
        """
        logger.debug(
            "Retrieving documents in collection '%s' (job_id=%s, skip=%d, limit=%d)",
            cls.collection_name, job_id, skip, limit,
        )
        return await cls.get_many({"job_id": job_id}, skip, limit)

    @classmethod
    async def get_by_source(
        cls, source: PaperSource, skip: int = 0, limit: int = 100
    ) -> list[Paper]:
        """
        Get documents with pagination and source filter.
        """
        logger.debug(
            "Retrieving documents in collection '%s' (source=%s, skip=%d, limit=%d)",
            cls.collection_name, source, skip, limit,
        )
        return await cls.get_many({"source": source}, skip, limit)

    @classmethod
    async def get_by_source_id(cls, source_id: str) -> Paper | None:
        """
        Get document by source ID.
        """
        logger.debug(
            "Retrieving document in collection '%s' (source_id=%s)",
            cls.collection_name, source_id,
        )
        return await cls.get_one({"source_id": source_id})
