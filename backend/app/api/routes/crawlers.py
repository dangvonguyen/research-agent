import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.deps import SessionDep
from app.db.queries import crawler as crawler_db
from app.services.crawler import crawler_service
from app.types import (
    CrawlerConfigCreate,
    CrawlerConfigResponse,
    CrawlerConfigUpdate,
    CrawlerJobCreate,
    CrawlerJobResponse,
    CrawlerJobUpdate,
    CreateResponse,
    DeleteResponse,
    JobStatus,
    UpdateResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/configs", response_model=CreateResponse)
async def create_crawler_config(
    session: SessionDep, config: CrawlerConfigCreate
) -> Any:
    """
    Create a new crawler configuration.
    """
    # Check if config with the same name already exists
    existing = await crawler_db.get_crawler_config_by_name(session, config.name)
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
    result = await crawler_db.create_crawler_config(session, config)
    logger.info(
        "Successfully created crawler configuration '%s' (ID: '%s')",
        config.name, result.id,
    )
    return CreateResponse(
        success=True,
        message="Crawler configuration successfully created",
        created_count=1,
        created_ids=[str(result.id)],
    )


@router.get("/configs", response_model=list[CrawlerConfigResponse])
async def get_crawler_configs(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> list[CrawlerConfigResponse]:
    """
    List all crawler configurations.
    """
    logger.debug(
        "Retrieving crawler configurations with skip=%d, limit=%d", skip, limit
    )
    configs = await crawler_db.get_crawler_configs(session, skip=skip, limit=limit)
    return [CrawlerConfigResponse.model_validate(config) for config in configs]


@router.get("/configs/{config_id}", response_model=CrawlerConfigResponse)
async def get_crawler_config(session: SessionDep, config_id: str) -> CrawlerConfigResponse:
    """
    Get a specific crawler configuration.
    """
    logger.debug("Retrieving crawler configuration with ID '%s'", config_id)
    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid config ID format")
    
    config = await crawler_db.get_crawler_config_by_id(session, config_uuid)
    if not config:
        logger.warning("Crawler configuration '%s' not found", config_id)
        raise HTTPException(status_code=404, detail="Crawler configuration not found")
    return CrawlerConfigResponse.model_validate(config)


@router.get("/configs/name/{name}", response_model=CrawlerConfigResponse)
async def get_crawler_config_by_name(session: SessionDep, name: str) -> CrawlerConfigResponse:
    """
    Get a specific crawler configuration by name.
    """
    logger.debug("Retrieving crawler configuration with name '%s'", name)
    config = await crawler_db.get_crawler_config_by_name(session, name)
    if not config:
        logger.warning("Crawler configuration with name '%s' not found", name)
        raise HTTPException(status_code=404, detail="Crawler configuration not found")
    return CrawlerConfigResponse.model_validate(config)


@router.patch("/configs/{config_id}", response_model=UpdateResponse)
async def update_crawler_config(
    session: SessionDep, config_id: str, config: CrawlerConfigUpdate
) -> Any:
    """
    Update a crawler configuration.
    """
    logger.debug("Updating crawler configuration '%s'", config_id)
    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid config ID format")
    
    updated = await crawler_db.update_crawler_config(session, config_uuid, config)
    if not updated:
        raise HTTPException(status_code=404, detail="Crawler configuration not found")
    
    return UpdateResponse(
        success=True,
        message="Crawler configuration successfully updated",
        matched_count=1,
        modified_count=1,
    )


@router.delete("/configs/{config_id}", response_model=DeleteResponse)
async def delete_crawler_config(session: SessionDep, config_id: str) -> Any:
    """
    Delete a crawler configuration.
    """
    logger.debug("Deleting crawler configuration '%s'", config_id)
    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid config ID format")
    
    deleted = await crawler_db.delete_crawler_config(session, config_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Crawler configuration not found")
    
    return DeleteResponse(
        success=True,
        message="Crawler configuration successfully deleted",
        deleted_count=1,
    )


@router.post("/jobs", response_model=CreateResponse)
async def create_crawler_job(
    session: SessionDep, job: CrawlerJobCreate, background_tasks: BackgroundTasks
) -> Any:
    """
    Create and start a new crawler job.
    """
    logger.info(
        "Creating new crawler job for config '%s' with %d URLs and query '%s'",
        job.config_name, len(job.urls) if job.urls else 0, job.query or "None",
    )
    if not job.urls and not job.query:
        logger.warning("Job must have either URLs or query")
        raise HTTPException(
            status_code=400,
            detail="Job must have either URLs or query",
        )

    # Verify config exists
    config = await crawler_db.get_crawler_config_by_name(session, job.config_name)
    if not config:
        logger.warning("Config '%s' not found for job creation", job.config_name)
        raise HTTPException(status_code=404, detail="Crawler configuration not found")

    # Create job in database
    result = await crawler_db.create_crawler_job(session, job)
    logger.info("Successfully created crawler job '%s'", result.id)

    # Schedule background task
    logger.debug("Scheduling background task for job '%s'", result.id)
    background_tasks.add_task(crawler_service.run_crawler_job, str(result.id))

    return CreateResponse(
        success=True,
        message="Crawler job successfully created",
        created_count=1,
        created_ids=[str(result.id)],
    )


@router.get("/jobs", response_model=list[CrawlerJobResponse])
async def get_crawler_jobs(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    status: JobStatus | None = None,
) -> list[CrawlerJobResponse]:
    logger.debug(
        "Retrieving crawler jobs with skip=%d, limit=%d, status=%s",
        skip, limit, status.value if status else "None",
    )
    jobs = await crawler_db.get_crawler_jobs(session, skip=skip, limit=limit, status=status)
    return [CrawlerJobResponse.model_validate(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=CrawlerJobResponse)
async def get_crawler_job(session: SessionDep, job_id: str) -> CrawlerJobResponse:
    """
    Get a crawler job.
    """
    logger.debug("Retrieving crawler job '%s'", job_id)
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    job = await crawler_db.get_crawler_job_by_id(session, job_uuid)
    if not job:
        logger.warning("Crawler job '%s' not found", job_id)
        raise HTTPException(status_code=404, detail="Crawler job not found")
    return CrawlerJobResponse.model_validate(job)


@router.patch("/jobs/{job_id}", response_model=UpdateResponse)
async def update_crawler_job(
    session: SessionDep, job_id: str, job: CrawlerJobUpdate
) -> Any:
    """
    Update a crawler job.
    """
    logger.debug("Updating crawler job '%s'", job_id)
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    updated = await crawler_db.update_crawler_job(session, job_uuid, job)
    if not updated:
        raise HTTPException(status_code=404, detail="Crawler job not found")
    
    return UpdateResponse(
        success=True,
        message="Crawler job successfully updated",
        matched_count=1,
        modified_count=1,
    )


@router.delete("/jobs/{job_id}", response_model=DeleteResponse)
async def delete_crawler_job(session: SessionDep, job_id: str) -> Any:
    """
    Delete a crawler job.
    """
    logger.debug("Deleting crawler job '%s'", job_id)
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    deleted = await crawler_db.delete_crawler_job(session, job_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Crawler job not found")
    
    return DeleteResponse(
        success=True,
        message="Crawler job successfully deleted",
        deleted_count=1,
    )
