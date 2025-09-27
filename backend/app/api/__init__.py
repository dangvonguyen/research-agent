from fastapi import APIRouter

from app.api.routes import chat, conversations, crawlers, papers

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(crawlers.router, prefix="/crawlers", tags=["crawlers"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
