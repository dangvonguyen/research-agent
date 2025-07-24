from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

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


class CrawlerConfigRepository(
    BaseRepository[CrawlerConfig, CrawlerConfigCreate, CrawlerConfigUpdate]
):
    """Repository for crawler configurations."""

    collection_name = "crawler_configs"
    model_class = CrawlerConfig


class CrawlerJobRepository(
    BaseRepository[CrawlerJob, CrawlerJobCreate, CrawlerJobUpdate]
):
    """Repository for crawler jobs."""

    collection_name = "crawler_jobs"
    model_class = CrawlerJob

    @classmethod
    async def list(
        cls, skip: int = 0, limit: int = 100, status: JobStatus | None = None
    ) -> list[CrawlerJob]:
        """
        List documents with pagination and status filter.
        """
        collection = mongodb.get_collection(cls.collection_name)

        objects = []

        if status:
            cursor = collection.find({"status": status.value})
        else:
            cursor = collection.find()
        cursor = cursor.skip(skip).limit(limit).sort("updated_at", -1)

        async for obj in cursor:
            obj["_id"] = str(obj["_id"])
            objects.append(cls.model_class(**obj))

        return objects

    @classmethod
    async def update_job_status(
        cls, id: str, status: JobStatus, **additional_fields: Any
    ) -> CrawlerJob | None:
        """
        Update a crawler job's status and additional fields.
        """
        collection = mongodb.get_collection(cls.collection_name)

        update_data = {"status": status.value, "updated_at": datetime.now(UTC)}
        update_data.update(additional_fields)

        result = await collection.update_one(
            {"_id": ObjectId(id)}, {"$set": update_data}
        )

        if result.modified_count:
            return await cls.get(id)
        else:
            return None
