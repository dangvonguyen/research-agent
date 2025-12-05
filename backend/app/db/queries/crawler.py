from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CrawlerConfig, CrawlerJob
from app.types import (
    CrawlerConfigCreate,
    CrawlerConfigUpdate,
    CrawlerJobCreate,
    CrawlerJobUpdate,
    JobStatus,
)


async def create_crawler_config(
    session: AsyncSession, config: CrawlerConfigCreate
) -> CrawlerConfig:
    """Create a new crawler configuration."""
    config_db = CrawlerConfig(**config.model_dump(exclude_unset=True))
    session.add(config_db)
    await session.commit()
    await session.refresh(config_db)
    return config_db


async def get_crawler_configs(
    session: AsyncSession, skip: int = 0, limit: int = 100
) -> list[CrawlerConfig]:
    """Get all crawler configurations."""
    stmt = (
        select(CrawlerConfig)
        .offset(skip)
        .limit(limit)
        .order_by(CrawlerConfig.updated_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_crawler_config_by_id(
    session: AsyncSession, config_id: UUID
) -> CrawlerConfig | None:
    """Get a crawler configuration by ID."""
    stmt = select(CrawlerConfig).where(CrawlerConfig.id == config_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_crawler_config_by_name(
    session: AsyncSession, name: str
) -> CrawlerConfig | None:
    """Get a crawler configuration by name."""
    stmt = select(CrawlerConfig).where(CrawlerConfig.name == name)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_crawler_config(
    session: AsyncSession, config_id: UUID, update_data: CrawlerConfigUpdate
) -> CrawlerConfig | None:
    """Update a crawler configuration."""
    stmt = select(CrawlerConfig).where(CrawlerConfig.id == config_id)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if not config:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(config, key, value)

    await session.commit()
    await session.refresh(config)
    return config


async def delete_crawler_config(session: AsyncSession, config_id: UUID) -> bool:
    """Delete a crawler configuration."""
    stmt = select(CrawlerConfig).where(CrawlerConfig.id == config_id)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if not config:
        return False

    await session.delete(config)
    await session.commit()
    return True


async def create_crawler_job(
    session: AsyncSession, job: CrawlerJobCreate
) -> CrawlerJob:
    """Create a new crawler job."""
    # Convert URLs from HttpUrl to strings if needed
    job_dict = job.model_dump(exclude_unset=True)
    if job_dict.get("urls"):
        job_dict["urls"] = [str(url) for url in job_dict["urls"]]

    job_db = CrawlerJob(**job_dict)
    session.add(job_db)
    await session.commit()
    await session.refresh(job_db)
    return job_db


async def get_crawler_jobs(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: JobStatus | None = None,
) -> list[CrawlerJob]:
    """Get crawler jobs with optional status filter."""
    stmt = select(CrawlerJob)
    if status:
        stmt = stmt.where(CrawlerJob.status == status)
    stmt = stmt.offset(skip).limit(limit).order_by(CrawlerJob.updated_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_crawler_job_by_id(
    session: AsyncSession, job_id: UUID
) -> CrawlerJob | None:
    """Get a crawler job by ID."""
    stmt = select(CrawlerJob).where(CrawlerJob.id == job_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_crawler_job(
    session: AsyncSession,
    job_id: UUID,
    update_data: CrawlerJobUpdate | None = None,
    **kwargs,
) -> CrawlerJob | None:
    """Update a crawler job."""
    stmt = select(CrawlerJob).where(CrawlerJob.id == job_id)
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        return None

    update_dict = {}
    if update_data:
        update_dict = update_data.model_dump(exclude_unset=True)
        # Convert URLs from HttpUrl to strings if needed
        if update_dict.get("urls"):
            update_dict["urls"] = [str(url) for url in update_dict["urls"]]

    update_dict.update(kwargs)

    for key, value in update_dict.items():
        setattr(job, key, value)

    await session.commit()
    await session.refresh(job)
    return job


async def delete_crawler_job(session: AsyncSession, job_id: UUID) -> bool:
    """Delete a crawler job."""
    stmt = select(CrawlerJob).where(CrawlerJob.id == job_id)
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        return False

    await session.delete(job)
    await session.commit()
    return True
