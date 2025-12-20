import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.main import api_router
from app.core.config import settings
from app.logging import setup_logging
from app.services.crawler import crawler_service
from app.services.zilliz_service import zilliz_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa
    """
    FastAPI lifespan event handler for startup and shutdown events.
    """
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    start_time = time.time()
    logger.info(
        "Starting application '%s' (version %s)",
        settings.PROJECT_NAME,
        settings.API_V1_STR,
    )

    # Initialize default crawler configurations
    try:
        await crawler_service.initialize_default_configs()
    except Exception as e:
        logger.error("Failed to initialize default crawler configs: %s", str(e))
        # Don't fail startup if config initialization fails

    # Initialize Zilliz/Milvus connection and collection
    try:
        zilliz_service.initialize()
    except Exception as e:
        logger.warning(
            "Failed to initialize Zilliz service at startup (will retry on first use): %s",
            str(e),
        )

    startup_time = time.time() - start_time
    logger.info(
        "Application startup completed successfully in %.2f seconds", startup_time
    )

    yield


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

# Mount static files for uploaded files
upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    f"{settings.API_V1_STR}/uploads",
    StaticFiles(directory=str(upload_dir)),
    name="uploads",
)


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint with API Information
    """
    logger = logging.getLogger(__name__)
    logger.debug("Root endpoint accessed")

    return {
        "message": "Research Agent API is running",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoints.
    """
    return {"status": "healthy"}
