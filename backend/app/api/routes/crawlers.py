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
    CreateResponse,
    DeleteResponse,
    JobStatus,
    PaperSource,
    UpdateResponse,
)
from app.repos import CrawlerConfigRepository, CrawlerJobRepository, PaperRepository
from app.tools.crawlers import ACLAnthologyCrawler
from app.tools.parsers import PDFParser
from app.utils import bulk_run

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/configs", response_model=CreateResponse)
async def create_crawler_config(config: CrawlerConfigCreate) -> Any:
    """
    Create a new crawler configuration.
    """
    # Check if config with the same name already exists
    existing = await CrawlerConfigRepository.get_by_name(config.name)
    if existing:
        logger.warning(
            "Crawler configuration with name '%s' already exists", config.name
        )
        raise HTTPException(
            status_code=409,
            detail=f"Crawler configuration with name '{config.name}' already exists",
        )

    logger.info(
        "Creating new crawler configuration '%s' for source '%s'",
        config.name, config.source.value,
    )
    result = await CrawlerConfigRepository.create_one(config)
    logger.info(
        "Successfully created crawler configuration '%s' (ID: '%s')",
        config.name, result.created_ids[0],
    )
    return result


@router.get("/configs", response_model=list[CrawlerConfig])
async def get_crawler_configs(skip: int = 0, limit: int = 100) -> Any:
    """
    List all crawler configurations.
    """
    logger.debug(
        "Retrieving crawler configurations with skip=%d, limit=%d", skip, limit
    )
    return await CrawlerConfigRepository.get_many(skip=skip, limit=limit)


@router.get("/configs/{config_id}", response_model=CrawlerConfig)
async def get_crawler_config(config_id: str) -> Any:
    """
    Get a specific crawler configuration.
    """
    logger.debug("Retrieving crawler configuration with ID '%s'", config_id)
    config = await CrawlerConfigRepository.get_by_id(config_id)
    if not config:
        logger.warning("Crawler configuration '%s' not found", config_id)
        raise HTTPException(status_code=404, detail="Crawler configuration not found")
    return config


@router.get("/configs/name/{name}", response_model=CrawlerConfig)
async def get_crawler_config_by_name(name: str) -> Any:
    """
    Get a specific crawler configuration by name.
    """
    logger.debug("Retrieving crawler configuration with name '%s'", name)
    config = await CrawlerConfigRepository.get_by_name(name)
    if not config:
        logger.warning("Crawler configuration with name '%s' not found", name)
        raise HTTPException(status_code=404, detail="Crawler configuration not found")
    return config


@router.patch("/configs/{config_id}", response_model=UpdateResponse)
async def update_crawler_config(
    config_id: str, config: CrawlerConfigUpdate
) -> Any:
    """
    Update a crawler configuration.
    """
    logger.debug("Updating crawler configuration '%s'", config_id)
    return await CrawlerConfigRepository.update_by_id(config_id, config)


@router.delete("/configs/{config_id}", response_model=DeleteResponse)
async def delete_crawler_config(config_id: str) -> Any:
    """
    Delete a crawler configuration.
    """
    logger.debug("Deleting crawler configuration '%s'", config_id)
    return await CrawlerConfigRepository.delete_by_id(config_id)


@router.post("/jobs", response_model=CreateResponse)
async def create_crawler_job(
    job: CrawlerJobCreate, background_tasks: BackgroundTasks
) -> Any:
    """
    Create and start a new crawler job.
    """
    logger.info(
        "Creating new crawler job for config '%s' with query '%s' and %d URLs",
        job.config_name, job.query or "", len(job.urls) if job.urls else 0,
    )
    if not job.query and not job.urls:
        logger.warning("Job must have either a query or URLs")
        raise HTTPException(
            status_code=400,
            detail="Job must have either a query or URLs",
        )

    # Verify config exists
    config = await CrawlerConfigRepository.get_by_name(job.config_name)
    if not config:
        logger.warning("Config '%s' not found for job creation", job.config_name)
        raise HTTPException(status_code=404, detail="Crawler configuration not found")

    # Create job in database
    result = await CrawlerJobRepository.create_one(job)
    logger.info("Successfully created crawler job '%s'", result.created_ids[0])

    # Schedule background task
    logger.debug("Scheduling background task for job '%s'", result.created_ids[0])
    background_tasks.add_task(run_crawler_job, result.created_ids[0])

    return result


@router.get("/jobs", response_model=list[CrawlerJob])
async def get_crawler_jobs(
    skip: int = 0, limit: int = 100, status: JobStatus | None = None
) -> Any:
    logger.debug(
        "Retrieving crawler jobs with skip=%d, limit=%d, status=%s",
        skip, limit, status.value if status else "None",
    )
    if status:
        jobs = await CrawlerJobRepository.get_by_status(status, skip, limit)
    else:
        jobs = await CrawlerJobRepository.get_many(skip=skip, limit=limit)
    return jobs


@router.get("/jobs/{job_id}", response_model=CrawlerJob)
async def get_crawler_job(job_id: str) -> Any:
    """
    Get a crawler job.
    """
    logger.debug("Retrieving crawler job '%s'", job_id)
    job = await CrawlerJobRepository.get_by_id(job_id)
    if not job:
        logger.warning("Crawler job '%s' not found", job_id)
        raise HTTPException(status_code=404, detail="Crawler job not found")
    return job


@router.patch("/jobs/{job_id}", response_model=UpdateResponse)
async def update_crawler_job(job_id: str, job: CrawlerJobUpdate) -> Any:
    """
    Update a crawler job.
    """
    logger.debug("Updating crawler job '%s'", job_id)
    return await CrawlerJobRepository.update_by_id(job_id, job)


@router.delete("/jobs/{job_id}", response_model=DeleteResponse)
async def delete_crawler_job(job_id: str) -> Any:
    """
    Delete a crawler job.
    """
    logger.debug("Deleting crawler job '%s'", job_id)
    return await CrawlerJobRepository.delete_by_id(job_id)


async def run_crawler_job(job_id: str) -> None:
    """
    Run a crawler job in the background.
    """
    logger.info("Starting background job execution for job '%s'", job_id)

    try:
        # Get job and config
        job = await CrawlerJobRepository.get_by_id(job_id)
        if not job:
            logger.error("Job '%s' not found when starting background execution", job_id)
            return

        logger.debug(
            "Fetching configuration for job '%s' (config name: %s)", job_id, job.config_name
        )
        config = await CrawlerConfigRepository.get_by_name(job.config_name)
        if not config:
            logger.error(
                "Configuration '%s' not found for job '%s'", job.config_name, job_id
            )
            await CrawlerJobRepository.update_job_status(
                job_id,
                status=JobStatus.FAILED,
                error_message=f"Configuration '{job.config_name}' not found",
            )
            return

        logger.info(
            "Starting job '%s' for config '%s' (source: %s)",
            job_id, job.config_name, config.source.value
        )

        # Update job status
        await CrawlerJobRepository.update_job_status(
            job_id,
            status=JobStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

        if config.source == PaperSource.ACL_ANTHOLOGY:
            logger.info("Starting ACL Anthology crawler for job '%s'", job_id)
            config_dict = config.model_dump(
                include=set(CrawlerConfigCreate.model_fields.keys()),
                exclude={"name"},
            )

            async with ACLAnthologyCrawler(**config_dict) as crawler:
                # Run the crawler
                urls = [url.encoded_string() for url in job.urls] if job.urls else None
                logger.info(
                    "Crawling %d URLs and query '%s' for job '%s'",
                    len(urls) if urls else 0, job.query or "", job_id,
                )
                papers = await crawler.crawl(job.query, urls)

                if not papers:
                    logger.warning("No papers found for job '%s'", job_id)
                    await CrawlerJobRepository.update_job_status(
                        job_id,
                        status=JobStatus.COMPLETED,
                        completed_at=datetime.now(UTC),
                    )
                    return

                # Download PDFs
                logger.info("Downloading %d PDFs for job '%s'", len(papers), job_id)
                await bulk_run(crawler.download_pdf, papers)

            # Parse papers
            parser = PDFParser()
            logger.info("Parsing %d papers for job '%s'", len(papers), job_id)
            section_types = ["abstract", "introduction", "conclusion"]
            for paper in papers:
                sections = parser.parse_specific_sections(paper, section_types)
                paper.sections = sections
                paper.job_id = job_id

            logger.info("Creating %d papers for job '%s'", len(papers), job_id)
            await PaperRepository.create_many(papers)
            logger.info(
                "Successfully created %d papers for job '%s'", len(papers), job_id
            )

            # Update job status
            logger.info("Crawler completed successfully for job '%s'", job_id)
            await CrawlerJobRepository.update_job_status(
                job_id,
                status=JobStatus.COMPLETED,
                completed_at=datetime.now(UTC),
            )
        else:
            logger.error(
                "Unsupported crawler source '%s' for job '%s'",
                config.source.value, job_id,
            )
            await CrawlerJobRepository.update_job_status(
                job_id,
                status=JobStatus.FAILED,
                error_message=f"Crawler source '{config.source.value}' not implemented",
            )

    except Exception as e:
        logger.exception("Error executing crawler job '%s': %s", job_id, str(e))
        await CrawlerJobRepository.update_job_status(
            job_id,
            status=JobStatus.FAILED,
            error_message=str(e),
        )
