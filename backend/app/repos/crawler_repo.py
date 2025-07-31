import logging
from typing import Any

from pymongo import IndexModel

from app.models import (
    CrawlerConfig,
    CrawlerConfigCreate,
    CrawlerConfigUpdate,
    CrawlerJob,
    CrawlerJobCreate,
    CrawlerJobUpdate,
    JobStatus,
    UpdateResponse,
)

from .base_repo import BaseRepository

logger = logging.getLogger(__name__)


class CrawlerConfigRepository(
    BaseRepository[CrawlerConfig, CrawlerConfigCreate, CrawlerConfigUpdate]
):
    """Repository for crawler configurations."""

    collection_name = "crawler_configs"
    model_class = CrawlerConfig
    indexes = [
        IndexModel([("name", 1)], name="crawler_config_name", unique=True),
    ]

    @classmethod
    async def get_by_name(cls, name: str) -> CrawlerConfig | None:
        """
        Get a crawler configuration by name.
        """
        logger.debug("Retrieving crawler config with name '%s'", name)
        return await cls.get_one({"name": name})


class CrawlerJobRepository(
    BaseRepository[CrawlerJob, CrawlerJobCreate, CrawlerJobUpdate]
):
    """Repository for crawler jobs."""

    collection_name = "crawler_jobs"
    model_class = CrawlerJob
    indexes = [
        IndexModel([("config_name", 1)], name="crawler_job_config_name"),
        IndexModel([("status", 1)], name="crawler_job_status"),
    ]

    @classmethod
    async def get_by_status(
        cls, status: JobStatus, skip: int = 0, limit: int = 100
    ) -> list[CrawlerJob]:
        """
        Get documents with pagination and status filter.
        """
        logger.debug(
            "Retrieving documents in collection '%s' (status=%s, skip=%d, limit=%d)",
            cls.collection_name, status.value, skip, limit,
        )
        return await cls.get_many({"status": status.value}, skip, limit)

    @classmethod
    async def get_by_config_name(
        cls, config_name: str, skip: int = 0, limit: int = 100
    ) -> list[CrawlerJob]:
        """
        Get documents with pagination and config name filter.
        """
        logger.debug(
            "Retrieving documents in collection '%s' (config_name=%s, skip=%d, limit=%d)",
            cls.collection_name, config_name,
        )
        return await cls.get_many({"config_name": config_name}, skip, limit)

    @classmethod
    async def update_job_status(
        cls, id: str, status: JobStatus, **additional_fields: Any
    ) -> UpdateResponse:
        """
        Update a crawler job's status and additional fields.
        """
        logger.info("Updating job '%s' status to %s", id, status.value)
        additional_fields["status"] = status.value
        return await cls.update_by_id(id, None, **additional_fields)
