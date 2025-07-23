from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class PaperSource(Enum):
    ACL_ANTHOLOGY = "acl_anthology"


class CrawlerRequest(BaseModel):
    urls: list[HttpUrl]
    source: PaperSource
    rate_limit: int = 20
    max_delay: int = 60
    max_attempts: int = 3
    max_concurrent: int = 10
    output_dir: str = "crawled_papers"


class CrawlerResponse(BaseModel):
    status: str
    message: str
    job_id: str


class CrawlerJobList(BaseModel):
    data: list[CrawlerResponse]
    count: int


class Paper(BaseModel):
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
