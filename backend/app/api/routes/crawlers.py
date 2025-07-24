import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models import (
    CrawlerConfig,
    CrawlerConfigCreate,
    CrawlerConfigUpdate,
    CrawlerJob,
    CrawlerJobCreate,
    CrawlerJobUpdate,
    JobStatus,
    PaperSource,
)
from app.repos import CrawlerConfigRepository, CrawlerJobRepository
from app.tools.crawlers import ACLAnthologyCrawler

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/configs", response_model=CrawlerConfig)
async def create_crawler_config(config: CrawlerConfigCreate) -> Any:
    """
    Create a new crawler configuration.
    """
    return await CrawlerConfigRepository.create(config)


@router.get("/configs", response_model=list[CrawlerConfig])
async def get_crawler_configs(skip: int = 0, limit: int = 100) -> Any:
    """
    List all crawler configurations.
    """
    return await CrawlerConfigRepository.list(skip, limit)


@router.get("/configs/{config_id}", response_model=CrawlerConfig)
async def get_crawler_config(config_id: str) -> Any:
    """
    Get a specific crawler configuration.
    """
    config = await CrawlerConfigRepository.get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Crawler configuration not found")
    return config


@router.patch("/configs/{config_id}", response_model=CrawlerConfig)
async def update_crawler_config(config_id: str, config: CrawlerConfigUpdate) -> Any:
    """
    Update a crawler configuration.
    """
    updated_config = await CrawlerConfigRepository.update(config_id, config)
    if not updated_config:
        raise HTTPException(status_code=404, detail="Crawler configuration not found")
    return updated_config


@router.delete("/configs/{config_id}", response_model=bool)
async def delete_crawler_config(config_id: str) -> Any:
    """
    Delete a crawler configuration.
    """
    success = await CrawlerConfigRepository.delete(config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Crawler configuration not found")
    return success


@router.post("/jobs", response_model=CrawlerJob)
async def create_crawler_job(
    job: CrawlerJobCreate, background_tasks: BackgroundTasks
) -> Any:
    """
    Create and start a new crawler job.
    """
    config = await CrawlerConfigRepository.get(job.config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Crawler configuration not found")

    created_job = await CrawlerJobRepository.create(job)

    background_tasks.add_task(run_crawler_job, created_job.id)

    return created_job


@router.get("/jobs", response_model=list[CrawlerJob])
async def get_crawler_jobs(
    skip: int = 0, limit: int = 100, status: JobStatus | None = None
) -> Any:
    """
    List all crawler jobs.
    """
    return await CrawlerJobRepository.list(skip, limit, status)


@router.get("/jobs/{job_id}", response_model=CrawlerJob)
async def get_crawler_job(job_id: str) -> Any:
    """
    Get a crawler job.
    """
    return await CrawlerJobRepository.get(job_id)


@router.patch("/jobs/{job_id}", response_model=CrawlerJob)
async def update_crawler_job(job_id: str, job: CrawlerJobUpdate) -> Any:
    """
    Update a crawler job.
    """
    updated_job = await CrawlerJobRepository.update(job_id, job)
    if not updated_job:
        raise HTTPException(status_code=404, detail="Crawler job not found")
    return updated_job


@router.delete("/jobs/{job_id}", response_model=bool)
async def delete_crawler_job(job_id: str) -> Any:
    """
    Delete a crawler job.
    """
    success = await CrawlerJobRepository.delete(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Crawler job not found")
    return success


async def run_crawler_job(job_id) -> None:
    """
    Run a crawler job in the background.
    """
    try:
        # Get job anc config
        job = await CrawlerJobRepository.get(job_id)
        if not job:
            return

        config = await CrawlerConfigRepository.get(job.config_id)
        if not config:
            await CrawlerJobRepository.update_job_status(
                job_id,
                status=JobStatus.FAILED,
                error_message="Crawler configuration not found",
            )
            return

        # Mark job as running
        await CrawlerJobRepository.update_job_status(
            job_id,
            status=JobStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

        if config.source == PaperSource.ACL_ANTHOLOGY:
            config_create = CrawlerConfigCreate(**config.model_dump())

            crawler = ACLAnthologyCrawler(**config_create.model_dump(exclude={"name"}))

            # Run the crawler
            urls = [str(url) for url in job.urls]
            await crawler.crawl(urls)

            await CrawlerJobRepository.update_job_status(
                job_id,
                status=JobStatus.COMPLETED,
                completed_at=datetime.now(UTC),
            )
        else:
            await CrawlerJobRepository.update_job_status(
                job_id,
                status=JobStatus.FAILED,
                error_message=f"Crawler source {config.source} not implemented",
            )

    except Exception as e:
        await CrawlerJobRepository.update_job_status(
            job_id,
            status=JobStatus.FAILED,
            error_message=str(e),
        )
