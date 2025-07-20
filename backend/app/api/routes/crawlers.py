import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import AnyHttpUrl, BaseModel, Field

from app.services.crawler import ACLAnthologyCrawler

router = APIRouter()


class CrawlerRequest(BaseModel):
    urls: list[AnyHttpUrl]
    output_dir: str = "crawled_papers"
    max_concurrent: int = 5
    delay: float = 0.5


class CrawlerResponse(BaseModel):
    status: str
    message: str
    job_id: str


class CrawlerJobList(BaseModel):
    data: list[CrawlerResponse]
    count: int


class PaperResponse(BaseModel):
    id: str
    title: str
    authors: list[str]
    anthology_url: str
    pdf_url: str | None = None
    abstract: str | None = None
    year: int | None = None
    venues: list[str] = Field(default_factory=list)


# In-memory storage for job status
crawler_jobs: dict[str, dict[str, Any]] = {}


@router.post("/jobs", response_model=CrawlerResponse)
async def create_crawler_job(
    request: CrawlerRequest, background_tasks: BackgroundTasks
) -> Any:
    """
    Start a crawling job to fetch papers from ACL Anthology.

    This endpoint will start a background task to crawl the specified URLs.
    """
    job_id = str(uuid.uuid4())

    # Store job information
    crawler_jobs[job_id] = {"status": "pending", "request": request}

    async def run_crawler_job() -> None:
        crawler = ACLAnthologyCrawler(
            output_dir=request.output_dir,
            max_concurrent=request.max_concurrent,
            delay=request.delay,
        )

        crawler_jobs[job_id]["status"] = "running"

        try:
            await crawler.crawl(urls=[str(url) for url in request.urls])
            crawler_jobs[job_id]["status"] = "completed"
        except Exception as e:
            crawler_jobs[job_id]["status"] = "failed"
            crawler_jobs[job_id]["error"] = str(e)

    background_tasks.add_task(run_crawler_job)

    return CrawlerResponse(
        status="accepted",
        message="Crawl job started",
        job_id=job_id,
    )


@router.get("/jobs", response_model=CrawlerJobList)
async def get_crawler_jobs() -> Any:
    jobs = []

    for job_id, job in crawler_jobs.items():
        jobs.append(
            CrawlerResponse(
                status=job["status"],
                message=f"Job is {job['status']}",
                job_id=job_id,
            )
        )

    return {"data": jobs, "count": len(jobs)}


@router.get("/jobs/{job_id}", response_model=CrawlerResponse)
async def get_crawler_job(job_id: str) -> Any:
    """
    Get the status of a crawling job.
    """
    if job_id not in crawler_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = crawler_jobs[job_id]

    return CrawlerResponse(
        status=job["status"],
        message=f"Job is {job['status']}",
        job_id=job_id,
    )
