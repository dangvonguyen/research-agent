from typing import Any

from bson.objectid import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import AnyHttpUrl, BaseModel, Field

from app.core.db import mongodb
from app.services.crawler import ACLAnthologyCrawler

router = APIRouter()


class CrawlerRequest(BaseModel):
    urls: list[AnyHttpUrl]
    output_dir: str = "crawled_papers"
    max_concurrent: int = 5
    delay: float = 3


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


@router.post("/jobs", response_model=CrawlerResponse)
async def create_crawler_job(
    request: CrawlerRequest, background_tasks: BackgroundTasks
) -> Any:
    """
    Start a crawling job to fetch papers from ACL Anthology.

    This endpoint will start a background task to crawl the specified URLs.
    """
    collection = await mongodb.get_collection('crawler_jobs')

    # Store job information
    crawler_job = await collection.insert_one(
        {"status": "pending", "request": request.model_dump_json()}
    )

    job_id = crawler_job.inserted_id

    async def run_crawler_job() -> None:
        crawler = ACLAnthologyCrawler(
            output_dir=request.output_dir,
            max_concurrent=request.max_concurrent,
            delay=request.delay,
        )

        await collection.update_one(
            {"_id": job_id}, {"$set": {"status": "running"}}
        )

        try:
            await crawler.crawl(urls=[str(url) for url in request.urls])
            await collection.update_one(
                {"_id": job_id}, {"$set": {"status": "completed"}}
            )
        except Exception as e:
            await collection.update_one(
                {"_id": job_id}, {"$set": {"status": "failed", "request.error": str(e)}}
            )

    background_tasks.add_task(run_crawler_job)

    return CrawlerResponse(
        status="accepted",
        message="Crawl job started",
        job_id=str(job_id),
    )


@router.get("/jobs", response_model=CrawlerJobList)
async def get_crawler_jobs() -> Any:
    collection = await mongodb.get_collection('crawler_jobs')

    jobs = []

    async for job in collection.find():
        jobs.append(
            CrawlerResponse(
                status=job["status"],
                message=f"Job is {job['status']}",
                job_id=str(job["_id"]),
            )
        )

    return {"data": jobs, "count": len(jobs)}


@router.get("/jobs/{job_id}", response_model=CrawlerResponse)
async def get_crawler_job(job_id: str) -> Any:
    """
    Get the status of a crawling job.
    """
    collection = await mongodb.get_collection('crawler_jobs')

    job = await collection.find_one({"_id": ObjectId(job_id)})

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return CrawlerResponse(
        status=job["status"],
        message=f"Job is {job['status']}",
        job_id=str(job["_id"]),
    )
