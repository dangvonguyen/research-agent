from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class PaperSource(Enum):
    ACL_ANTHOLOGY = "acl_anthology"


class JobStatus(Enum):
    """Status of processing a job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseCreate(BaseModel):
    """Base model for all create operations."""

    pass


class BaseUpdate(BaseModel):
    """Base model for all update operations."""

    pass


class BaseDocument(BaseModel):
    """Base model for all database documents."""

    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
    }


class CrawlerConfigBase(BaseModel):
    """Base model for crawler configurations."""

    name: str
    source: PaperSource
    rate_limit: int = Field(default=10, ge=1)
    max_delay: int = Field(default=60, ge=1)
    max_attempts: int = Field(default=3, ge=1)
    max_concurrent: int = Field(default=10, ge=1)
    output_dir: str = "crawled_papers"


class CrawlerConfigCreate(BaseCreate, CrawlerConfigBase):
    """Model for creating a new crawler configuration."""

    pass


class CrawlerConfigUpdate(BaseUpdate):
    """Model for updating an existing crawler configuration."""

    name: str | None = None
    source: PaperSource | None = None
    rate_limit: int | None = None
    max_delay: int | None = None
    max_attempts: int | None = None
    max_concurrent: int | None = None
    output_dir: str | None = None


class CrawlerConfig(BaseDocument, CrawlerConfigBase):
    """Model for crawler configuration stored in database."""

    pass


class CrawlerJobBase(BaseModel):
    """Base model for crawler jobs."""

    config_id: str
    urls: list[HttpUrl]
    status: JobStatus = JobStatus.PENDING


class CrawlerJobCreate(BaseCreate, CrawlerJobBase):
    """Model for creating a new crawler job."""

    pass


class CrawlerJobUpdate(BaseUpdate):
    """Model for updating an existing crawler job."""

    urls: list[HttpUrl] | None = None
    status: JobStatus | None = None


class CrawlerJob(BaseDocument, CrawlerJobBase):
    """Model for crawler job stored in database."""

    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class PaperBase(BaseModel):
    """Base model for paper metadata."""

    title: str
    authors: list[str]
    source: PaperSource
    source_id: str
    abstract: str | None = None
    year: int | None = None
    url: str | None = None
    pdf_url: str | None = None
    local_pdf_path: str | None = None
    venues: list[str] = Field(default_factory=list)


class PaperCreate(BaseCreate, PaperBase):
    """Model for creating a new paper."""

    pass


class PaperUpdate(BaseUpdate):
    """Model for updating an existing paper."""

    title: str | None = None
    authors: list[str] | None = None
    source: PaperSource | None = None
    source_id: str | None = None
    abstract: str | None = None
    year: int | None = None
    url: str | None = None
    pdf_url: str | None = None
    local_pdf_path: str | None = None
    venues: list[str] | None = None


class Paper(BaseDocument, PaperBase):
    """Model for paper stored in database."""

    pass
