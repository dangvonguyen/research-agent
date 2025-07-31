import logging

from pymongo import IndexModel

from app.models import (
    CrawlerConfig,
    CrawlerConfigCreate,
    CrawlerConfigUpdate,
    CrawlerJob,
    CrawlerJobCreate,
    CrawlerJobUpdate,
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
