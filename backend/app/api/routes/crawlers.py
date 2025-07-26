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
from app.repos import CrawlerConfigRepository, CrawlerJobRepository, PaperRepository
from app.tools.crawlers import ACLAnthologyCrawler
from app.tools.parsers import PDFParser

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/configs", response_model=CrawlerConfig)
async def create_crawler_config(config: CrawlerConfigCreate) -> Any:
    """
    Create a new crawler configuration.
    """
    logger.info(
        "Creating new crawler configuration: '%s' for source %s",
        config.name, config.source,
    )
    result = await CrawlerConfigRepository.create(config)
    logger.debug("Created crawler configuration with ID: %s", result.id)
    return result


@router.get("/configs", response_model=list[CrawlerConfig])
async def get_crawler_configs(skip: int = 0, limit: int = 100) -> Any:
    """
    List all crawler configurations.
    """
    logger.debug(
        "Retrieving crawler configurations with skip=%d, limit=%d", skip, limit
    )
    configs = await CrawlerConfigRepository.list(skip, limit)
    logger.debug("Found %d crawler configurations", len(configs))
    return configs


@router.get("/configs/{config_id}", response_model=CrawlerConfig)
async def get_crawler_config(config_id: str) -> Any:
    """
    Get a specific crawler configuration.
    """
    logger.debug("Retrieving crawler configuration with ID: %s", config_id)
    config = await CrawlerConfigRepository.get(config_id)
    if not config:
        logger.warning("Crawler configuration not found: %s", config_id)
        raise HTTPException(status_code=404, detail="Crawler configuration not found")
    return config


@router.patch("/configs/{config_id}", response_model=CrawlerConfig)
async def update_crawler_config(config_id: str, config: CrawlerConfigUpdate) -> Any:
    """
    Update a crawler configuration.
    """
    logger.info("Updating crawler configuration: %s", config_id)
    logger.debug("Update data: %s", config.model_dump(exclude_unset=True))

    updated_config = await CrawlerConfigRepository.update(config_id, config)
    if not updated_config:
        logger.warning("Crawler configuration not found for update: %s", config_id)
        raise HTTPException(status_code=404, detail="Crawler configuration not found")

    logger.info("Successfully updated crawler configuration: %s", config_id)
    return updated_config


@router.delete("/configs/{config_id}", response_model=bool)
async def delete_crawler_config(config_id: str) -> Any:
    """
    Delete a crawler configuration.
    """
    logger.info("Deleting crawler configuration: %s", config_id)
    success = await CrawlerConfigRepository.delete(config_id)
    if not success:
        logger.warning("Crawler configuration not found for deletion: %s", config_id)
        raise HTTPException(status_code=404, detail="Crawler configuration not found")

    logger.info("Successfully deleted crawler configuration: %s", config_id)
    return success


@router.post("/jobs", response_model=CrawlerJob)
async def create_crawler_job(
    job: CrawlerJobCreate, background_tasks: BackgroundTasks
) -> Any:
    """
    Create and start a new crawler job.
    """
    logger.info(
        "Creating new crawler job for config: %s with %d URLs",
        job.config_id, len(job.urls),
    )

    # Verify config exists
    config = await CrawlerConfigRepository.get(job.config_id)
    if not config:
        logger.warning("Config not found for job creation: %s", job.config_id)
        raise HTTPException(status_code=404, detail="Crawler configuration not found")

    # Create job in database
    created_job = await CrawlerJobRepository.create(job)
    logger.info("Created crawler job with ID: %s", created_job.id)

    # Schedule background task
    logger.debug("Scheduling background task for job: %s", created_job.id)
    background_tasks.add_task(run_crawler_job, created_job.id)

    return created_job


@router.get("/jobs", response_model=list[CrawlerJob])
async def get_crawler_jobs(
    skip: int = 0, limit: int = 100, status: JobStatus | None = None
) -> Any:
    logger.debug(
        "Retrieving crawler jobs with skip=%d, limit=%d, status=%s",
        skip, limit, status.value if status else "None",
    )
    jobs = await CrawlerJobRepository.list(skip, limit, status)
    logger.debug("Found %d crawler jobs", len(jobs))
    return jobs


@router.get("/jobs/{job_id}", response_model=CrawlerJob)
async def get_crawler_job(job_id: str) -> Any:
    """
    Get a crawler job.
    """
    logger.debug("Retrieving crawler job with ID: %s", job_id)
    job = await CrawlerJobRepository.get(job_id)
    if not job:
        logger.warning("Crawler job not found: %s", job_id)
        raise HTTPException(status_code=404, detail="Crawler job not found")
    return job


@router.patch("/jobs/{job_id}", response_model=CrawlerJob)
async def update_crawler_job(job_id: str, job: CrawlerJobUpdate) -> Any:
    """
    Update a crawler job.
    """
    logger.info("Updating crawler job: %s", job_id)
    logger.debug("Update data: %s", job.model_dump(exclude_unset=True))

    updated_job = await CrawlerJobRepository.update(job_id, job)
    if not updated_job:
        logger.warning("Crawler job not found for update: %s", job_id)
        raise HTTPException(status_code=404, detail="Crawler job not found")

    logger.info("Successfully updated crawler job: %s", job_id)
    return updated_job


@router.delete("/jobs/{job_id}", response_model=bool)
async def delete_crawler_job(job_id: str) -> Any:
    """
    Delete a crawler job.
    """
    logger.info("Deleting crawler job: %s", job_id)
    success = await CrawlerJobRepository.delete(job_id)
    if not success:
        logger.warning("Crawler job not found for deletion: %s", job_id)
        raise HTTPException(status_code=404, detail="Crawler job not found")

    logger.info("Successfully deleted crawler job: %s", job_id)
    return success


async def run_crawler_job(job_id: str) -> None:
    """
    Run a crawler job in the background.
    """
    logger.info("Starting background job execution for job: %s", job_id)

    try:
        # Get job and config
        job = await CrawlerJobRepository.get(job_id)
        if not job:
            logger.error("Job not found when starting background execution: %s", job_id)
            return

        logger.debug(
            "Fetching configuration for job: %s (config_id: %s)", job_id, job.config_id
        )
        config = await CrawlerConfigRepository.get(job.config_id)
        if not config:
            logger.error(
                "Configuration not found for job %s: %s", job_id, job.config_id
            )
            await CrawlerJobRepository.update_job_status(
                job_id,
                status=JobStatus.FAILED,
                error_message="Crawler configuration not found",
            )
            return

        # Mark job as running
        logger.info("Updating job %s status to RUNNING", job_id)
        await CrawlerJobRepository.update_job_status(
            job_id,
            status=JobStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

        if config.source == PaperSource.ACL_ANTHOLOGY:
            logger.info("Starting ACL Anthology crawler for job %s", job_id)
            config_dict = config.model_dump(
                include=set(CrawlerConfigCreate.model_fields.keys()),
                exclude={"name"},
            )

            crawler = ACLAnthologyCrawler(**config_dict)

            # Run the crawler
            urls = [str(url) for url in job.urls]
            logger.info("Crawling %d URLs for job %s", len(urls), job_id)
            papers = await crawler.crawl(urls)

            # Parse papers
            parser = PDFParser()
            logger.info("Parsing %d papers for job %s", len(papers), job_id)
            for paper in papers:
                sections = parser.parse_specific_sections(
                    paper, ["abstract", "introduction", "conclusion"]
                )
                paper.sections = sections

            logger.info("Creating %d papers for job %s", len(papers), job_id)
            await PaperRepository.create_many(papers)
            logger.info(
                "Successfully created %d papers for job %s", len(papers), job_id
            )

            # Update job status
            logger.info("Crawler completed successfully for job %s", job_id)
            await CrawlerJobRepository.update_job_status(
                job_id,
                status=JobStatus.COMPLETED,
                completed_at=datetime.now(UTC),
            )
        else:
            logger.error(
                "Unsupported crawler source %s for job %s", config.source, job_id
            )
            await CrawlerJobRepository.update_job_status(
                job_id,
                status=JobStatus.FAILED,
                error_message=f"Crawler source {config.source} not implemented",
            )

    except Exception as e:
        logger.exception("Error executing crawler job %s: %s", job_id, str(e))
        await CrawlerJobRepository.update_job_status(
            job_id,
            status=JobStatus.FAILED,
            error_message=str(e),
        )
