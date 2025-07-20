from fastapi import APIRouter

from app.api.routes import crawlers

api_router = APIRouter()
api_router.include_router(crawlers.router, prefix="/crawlers", tags=["crawlers"])
