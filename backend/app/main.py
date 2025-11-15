import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import settings
from app.core.mongodb import mongodb
from app.logging import setup_logging
from app.repos import create_indexes
from app.services.crawler import initialize_default_configs


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
        settings.PROJECT_NAME, settings.API_V1_STR,
    )

    # Initialize default crawler configurations
    try:
        await initialize_default_configs()
    except Exception as e:
        logger.error("Failed to initialize default crawler configs: %s", str(e))
        # Don't fail startup if config initialization fails

    # # Connect to MongoDB
    # logger.info("Establishing connection to MongoDB at %s", settings.MONGODB_URI_SAFE)
    # await mongodb.connect()

    # # Create database indexes
    # logger.info("Creating database indexes")
    # await create_indexes()
    # logger.info("Successfully created database indexes")

    startup_time = time.time() - start_time
    logger.info(
        "Application startup completed successfully in %.2f seconds", startup_time
    )

    yield

    # # Shutdown process
    # logger.info("Beginning application shutdown process")
    # await mongodb.disconnect()
    # logger.info("Application '%s' shutdown completed", settings.PROJECT_NAME)


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
    # logger = logging.getLogger(__name__)
    # db_status = await mongodb.health_check()
    # status = "healthy" if db_status else "database_error"

    # if db_status:
    #     logger.debug("Health check passed: API and database connection OK")
    # else:
    #     logger.warning("Health check detected: database connection issue")

    return {"status": "healthy"}
