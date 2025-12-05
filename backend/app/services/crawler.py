import logging
from datetime import UTC, datetime
from uuid import UUID

from app.api.deps import Session
from app.db.queries import crawler as crawler_db
from app.db.queries import paper as paper_db
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service
from app.tools.crawlers import ACLAnthologyCrawler
from app.tools.parsers import PDFParser
from app.types import CrawlerConfigCreate, JobStatus, PaperSource
from app.utils import bulk_run

logger = logging.getLogger(__name__)


class CrawlerService:
    """Service for managing crawler operations."""

    async def initialize_default_configs(self) -> None:
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


    async def run_crawler_job(self, job_id: str) -> None:
        """
        Run a crawler job in the background.
        """
        logger.info("Starting background job execution for job '%s'", job_id)

        # Create a new session for the background task
        async with Session() as session:
            try:
                # Get job and config
                try:
                    job_uuid = UUID(job_id)
                except ValueError:
                    logger.error("Invalid job ID format '%s'", job_id)
                    return

                job = await crawler_db.get_crawler_job_by_id(session, job_uuid)
                if not job:
                    logger.error("Job '%s' not found when starting background execution", job_id)
                    return

                logger.debug(
                    "Fetching configuration for job '%s' (config name: %s)", job_id, job.config_name
                )
                config = await crawler_db.get_crawler_config_by_name(session, job.config_name)
                if not config:
                    logger.error(
                        "Configuration '%s' not found for job '%s'", job.config_name, job_id
                    )
                    await crawler_db.update_crawler_job(
                        session,
                        job_uuid,
                        None,
                        status=JobStatus.FAILED,
                        error_message=f"Configuration '{job.config_name}' not found",
                    )
                    return

                logger.info(
                    "Starting job '%s' for config '%s' (source: %s)",
                    job_id, job.config_name, config.source.value
                )

                # Update job status
                await crawler_db.update_crawler_job(
                    session,
                    job_uuid,
                    None,
                    status=JobStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )

                if config.source == PaperSource.ACL_ANTHOLOGY:
                    logger.info("Starting ACL Anthology crawler for job '%s'", job_id)
                    config_dict = {
                        "source": config.source,
                        "rate_limit": config.rate_limit,
                        "max_delay": config.max_delay,
                        "max_attempts": config.max_attempts,
                        "max_concurrent": config.max_concurrent,
                        "output_dir": config.output_dir,
                    }

                    async with ACLAnthologyCrawler(**config_dict) as crawler:
                        # Run the crawler
                        urls = job.urls if job.urls else None
                        query = job.query if job.query else None
                        
                        # If query is provided, enhance it with LLM first
                        if query:
                            logger.info("Enhancing search query with LLM for job '%s'", job_id)
                            try:
                                enhanced_query = await llm_service.enhance_search_keywords(query)
                                query = enhanced_query
                                logger.info("Enhanced query for job '%s': '%s' -> '%s'", job_id, job.query, query)
                            except Exception as e:
                                logger.error("Failed to enhance query for job '%s': %s", job_id, str(e))
                                # Fallback to original query if enhancement fails
                                query = job.query
                        
                        logger.info(
                            "Crawling %d URLs and query '%s' for job '%s'",
                            len(urls) if urls else 0, query or "None", job_id,
                        )
                        papers = await crawler.crawl(query, urls, job.max_papers)

                        if not papers:
                            logger.warning("No papers found for job '%s'", job_id)
                            await crawler_db.update_crawler_job(
                                session,
                                job_uuid,
                                None,
                                status=JobStatus.COMPLETED,
                                completed_at=datetime.now(UTC),
                            )
                            return

                        # Save papers immediately with job_id (so they appear in library)
                        logger.info("Creating %d papers for job '%s' (initial save)", len(papers), job_id)
                        created_papers = await paper_db.create_papers(session, papers, job_uuid)
                        logger.info(
                            "Successfully created %d papers for job '%s'", len(papers), job_id
                        )
                        
                        # Commit so papers appear immediately
                        await session.commit()

                        # Download PDFs
                        logger.info("Downloading %d PDFs for job '%s'", len(papers), job_id)
                        await bulk_run(crawler.download_pdf, papers)

                    # Parse papers and persist sections using ORM models
                    parser = PDFParser()
                    logger.info("Parsing %d papers for job '%s'", len(created_papers), job_id)
                    papers_to_embed = []
                    for paper_db_obj in created_papers:
                        contents = parser.parse_specific_sections(paper_db_obj)
                        if contents:
                            # Extract abstract from parsed contents if found
                            abstract_chunks = []
                            for content_obj in contents:
                                # Check if this is an abstract section
                                if content_obj.section_name and "abstract" in content_obj.section_name.lower():
                                    abstract_chunks.append(content_obj.content)
                            
                            # Combine abstract chunks if found
                            if abstract_chunks:
                                abstract_content = " ".join(abstract_chunks).strip()
                                # Clean up the abstract (remove extra whitespace)
                                abstract_content = " ".join(abstract_content.split())
                                if abstract_content and not paper_db_obj.abstract:
                                    # Only update if paper doesn't already have an abstract
                                    paper_db_obj.abstract = abstract_content
                                    logger.info(
                                        "Extracted abstract from parsed content for paper '%s' (length: %d)",
                                        paper_db_obj.id,
                                        len(abstract_content),
                                    )
                            
                            # Persist PaperContent rows and mark paper as parsed
                            session.add_all(contents)
                            paper_db_obj.parsed = True
                            papers_to_embed.append(paper_db_obj.id)

                    await session.commit()
                    
                    # Schedule background tasks to generate embeddings and store in Zilliz
                    # Run embeddings after commit to ensure data is persisted
                    for paper_id in papers_to_embed:
                        try:
                            # Run embedding in background (fire and forget)
                            import asyncio
                            asyncio.create_task(
                                embedding_service.embed_paper_chunks(paper_id)
                            )
                            logger.debug("Scheduled embedding task for paper '%s'", paper_id)
                        except Exception as e:
                            logger.error(
                                "Failed to schedule embedding task for paper '%s': %s",
                                paper_id,
                                str(e),
                            )

                    # Update job status
                    logger.info("Crawler completed successfully for job '%s'", job_id)
                    await crawler_db.update_crawler_job(
                        session,
                        job_uuid,
                        None,
                        status=JobStatus.COMPLETED,
                        completed_at=datetime.now(UTC),
                    )
                else:
                    logger.error(
                        "Unsupported crawler source '%s' for job '%s'",
                        config.source.value, job_id,
                    )
                    await crawler_db.update_crawler_job(
                        session,
                        job_uuid,
                        None,
                        status=JobStatus.FAILED,
                        error_message=f"Crawler source '{config.source.value}' not implemented",
                    )

            except Exception as e:
                logger.exception("Error executing crawler job '%s': %s", job_id, str(e))
                try:
                    job_uuid = UUID(job_id)
                    await crawler_db.update_crawler_job(
                        session,
                        job_uuid,
                        None,
                        status=JobStatus.FAILED,
                        error_message=str(e),
                    )
                except Exception as update_error:
                    logger.error("Failed to update job status: %s", str(update_error))


# Create singleton instance
crawler_service = CrawlerService()

