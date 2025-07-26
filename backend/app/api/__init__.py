from fastapi import APIRouter

from app.api.routes import crawlers, papers

api_router = APIRouter()
api_router.include_router(crawlers.router, prefix="/crawlers", tags=["crawlers"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
