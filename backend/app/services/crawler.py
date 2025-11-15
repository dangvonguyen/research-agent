import logging

from app.api.deps import Session
from app.db.queries import crawler as crawler_db
from app.types import CrawlerConfigCreate, PaperSource

logger = logging.getLogger(__name__)


async def initialize_default_configs() -> None:
    """
    Initialize default crawler configurations on application startup.
    Creates default configs if they don't already exist.
    """
    logger.info("Initializing default crawler configurations...")
    
    # Define default configurations
    default_configs = [
        CrawlerConfigCreate(
            name="default_acl_anthology",
            source=PaperSource.ACL_ANTHOLOGY,
            rate_limit=10,
            max_delay=60,
            max_attempts=3,
            max_concurrent=10,
            output_dir="crawled_papers",
        ),
    ]
    
    # Create a session for initialization
    async with Session() as session:
        created_count = 0
        skipped_count = 0
        
        for config_data in default_configs:
            try:
                # Check if config already exists
                existing = await crawler_db.get_crawler_config_by_name(
                    session, config_data.name
                )
                
                if existing:
                    logger.debug(
                        "Crawler configuration '%s' already exists, skipping",
                        config_data.name,
                    )
                    skipped_count += 1
                else:
                    # Create the config
                    await crawler_db.create_crawler_config(session, config_data)
                    logger.info(
                        "Created default crawler configuration '%s' for source '%s'",
                        config_data.name,
                        config_data.source.value,
                    )
                    created_count += 1
                    
            except Exception as e:
                logger.error(
                    "Error creating default config '%s': %s",
                    config_data.name,
                    str(e),
                )
                # Continue with other configs even if one fails
                continue
        
        if created_count > 0:
            logger.info(
                "Initialized %d default crawler configuration(s), %d already existed",
                created_count,
                skipped_count,
            )
        else:
            logger.info(
                "All default crawler configurations already exist (%d skipped)",
                skipped_count,
            )

