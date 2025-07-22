import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.db import mongodb
from app.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan event handler for startup and shutdown events.
    """
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    start_time = time.time()
    logger.info("Starting %s (version %s)", settings.PROJECT_NAME, settings.API_V1_STR)

    # Connect to MongoDB
    logger.info("Connecting to MongoDB...")
    await mongodb.connect()

    startup_time = time.time() - start_time
    logger.info("Application startup completed in %.2f seconds", startup_time)

    yield

    await mongodb.disconnect()

    logger.info("Shutting down application %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint with API Information
    """
    return {
        "message": "Research Agent API is running",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoints.
    """
    return {"status": "healthy"}
