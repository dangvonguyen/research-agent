import logging
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pymongo import IndexModel

from app.core.db import mongodb
from app.models import (
    CrawlerConfig,
    CrawlerConfigCreate,
    CrawlerConfigUpdate,
    CrawlerJob,
    CrawlerJobCreate,
    CrawlerJobUpdate,
    JobStatus,
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
    async def list(
        cls, skip: int = 0, limit: int = 100, status: JobStatus | None = None
    ) -> list[CrawlerJob]:
        """
        List documents with pagination and status filter.
        """
        logger.debug(
            "Retrieving documents from '%s' (skip=%d, limit=%d, status: %s)",
            cls.collection_name, skip, limit, status.value if status else "None",
        )
        collection = mongodb.get_collection(cls.collection_name)

        try:
            objects = []

            if status:
                cursor = collection.find({"status": status.value})
            else:
                cursor = collection.find()
            cursor = cursor.skip(skip).limit(limit).sort("updated_at", -1)

            doc_count = 0
            async for obj in cursor:
                obj["_id"] = str(obj["_id"])
                objects.append(cls.model_class(**obj))
                doc_count += 1

            logger.debug(
                "Successfully retrieved %d documents from collection '%s'",
                doc_count, cls.collection_name,
            )
            return objects

        except Exception as e:
            logger.error(
                "Error retrieving documents from '%s': %s", cls.collection_name, str(e)
            )
            raise

    @classmethod
    async def update_job_status(
        cls, id: str, status: JobStatus, **additional_fields: Any
    ) -> CrawlerJob | None:
        """
        Update a crawler job's status and additional fields.
        """
        logger.info("Updating job '%s' status to %s", id, status.value)

        if additional_fields:
            logger.debug(
                "Additional fields for job '%s' update: %s",
                id, ", ".join(f"{k}={v}" for k, v in additional_fields.items()),
            )

        collection = mongodb.get_collection(cls.collection_name)

        update_data = {"status": status.value, "updated_at": datetime.now(UTC)}
        update_data.update(additional_fields)

        try:
            result = await collection.update_one(
                {"_id": ObjectId(id)}, {"$set": update_data}
            )

            if result.matched_count == 0:
                logger.warning("Job '%s' not found for status update", id)
                return None

            if result.modified_count > 0:
                logger.debug(
                    "Job '%s' status updated successfully to %s", id, status.value
                )
            else:
                logger.debug("Job '%s' found but no changes made to status", id)

            return await cls.get(id)

        except Exception as e:
            logger.error("Error updating job '%s' status: %s", id, str(e))
            raise
