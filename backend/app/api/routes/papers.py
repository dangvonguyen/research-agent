import logging
import uuid
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.api.deps import SessionDep
from app.core.config import settings
from app.db.queries import paper as paper_db
from app.services.embedding_service import embedding_service
from app.services.paper_service import paper_service
from app.tools.parsers import PDFParser
from app.types import (
    CreateResponse,
    DeleteResponse,
    PaperCreate,
    PaperResponse,
    PaperUpdate,
    UpdateResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Ensure upload directory exists
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("", response_model=CreateResponse)
async def create_paper(session: SessionDep, paper: PaperCreate) -> Any:
    """
    Create a new paper stored in Postgres.
    """
    logger.info(
        "Creating new paper '%s' with source type '%s'",
        paper.title,
        paper.source_type,
    )
    result = await paper_db.create_paper(session, paper)
    logger.info(
        "Successfully created paper '%s' with ID '%s'",
        paper.title,
        result.id,
    )
    return CreateResponse(
        success=True,
        message="Paper successfully created",
        created_count=1,
        created_ids=[str(result.id)],
    )


@router.post("/upload", response_model=CreateResponse)
async def upload_paper(
    session: SessionDep,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
    abstract: Annotated[str | None, Form()] = None,
    doi: Annotated[str | None, Form()] = None,
    year: Annotated[int | None, Form()] = None,
    authors: Annotated[str | None, Form(description="Comma-separated")] = None,
    keywords: Annotated[str | None, Form(description="Comma-separated")] = None,
) -> Any:
    """
    Upload a PDF paper file with optional metadata.

    If metadata is provided by the user, it will be used.
    If metadata is missing, it will be extracted from the PDF.
    User-provided metadata takes precedence over extracted metadata.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Validate file size
    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / (1024 * 1024)}MB",
        )

    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename

    try:
        # Save file to disk
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        logger.info(
            "Successfully uploaded file '%s' as '%s' (size: %d bytes)",
            file.filename,
            unique_filename,
            file_size,
        )

        # Prepare metadata dictionary
        user_metadata = {
            "title": title.strip() if title and title.strip() else None,
            "authors": [a.strip() for a in authors.split(",")]
            if authors and authors.strip()
            else None,
            "abstract": abstract.strip() if abstract and abstract.strip() else None,
            "doi": doi.strip() if doi and doi.strip() else None,
            "year": year,
            "keywords": [k.strip() for k in keywords.split(",")]
            if keywords and keywords.strip()
            else None,
        }

        # Extract metadata from PDF if user didn't provide it
        parsed_metadata = {}
        parser = PDFParser()
        full_markdown_content = None

        try:
            # Get full markdown content once (will be reused for content parsing)
            logger.debug("Converting PDF to markdown for '%s'", file.filename)
            full_markdown_content = parser.get_markdown_content(
                str(file_path), max_pages=None
            )

            # Extract metadata from full markdown (abstract can be anywhere in document)
            parsed_metadata = paper_service.extract_metadata_from_markdown(
                full_markdown_content
            )

            logger.info(
                "Extracted metadata from PDF '%s': title='%s', authors=%s, year=%s",
                file.filename,
                parsed_metadata.get("title"),
                parsed_metadata.get("authors"),
                parsed_metadata.get("year"),
            )
        except Exception as e:
            logger.warning(
                "Failed to extract metadata from PDF '%s': %s. Using user-provided or filename as fallback.",
                file.filename,
                str(e),
            )
            # Continue with user metadata or filename as fallback

        # Merge metadata: user-provided takes precedence, then parsed, then fallback
        final_metadata = {
            "title": user_metadata["title"]
            or parsed_metadata.get("title")
            or Path(file.filename).stem,
            "authors": user_metadata["authors"] or parsed_metadata.get("authors"),
            "abstract": user_metadata["abstract"] or parsed_metadata.get("abstract"),
            "year": user_metadata["year"] or parsed_metadata.get("year"),
            "venue": parsed_metadata.get("venue"),  # Venue is only from parsing
        }

        # Create Paper record
        paper_create = PaperCreate(
            title=final_metadata["title"],
            authors=final_metadata["authors"],
            year=final_metadata["year"],
            venue=final_metadata["venue"],
            abstract=final_metadata["abstract"],
            source_type="upload",
            file_path=str(file_path),
            source_url=None,
        )

        # Create paper in database
        paper_orm = await paper_db.create_paper(session, paper_create)

        # Parse PDF content using the already-converted markdown (avoid re-parsing)
        try:
            logger.info("Parsing PDF content for paper '%s'", paper_orm.id)
            # Pass the pre-converted markdown to avoid re-parsing the PDF
            contents = parser.parse_paper(
                paper_orm, markdown_content=full_markdown_content
            )

            if contents:
                # Update paper with parsed contents
                from app.db.models import PaperContent as PaperContentORM

                content_objects = []

                # Extract abstract from parsed contents if found
                abstract_content = None
                abstract_chunks = []

                for content_data in contents:
                    # Check if this is an abstract section
                    if (
                        content_data.section_name
                        and "abstract" in content_data.section_name.lower()
                    ):
                        abstract_chunks.append(content_data.content)

                    content_objects.append(
                        PaperContentORM(
                            paper_id=paper_orm.id,
                            section_name=content_data.section_name,
                            section_index=content_data.section_index or 0,
                            chunk_index=content_data.chunk_index or 0,
                            content=content_data.content,
                            token_count=content_data.token_count,
                            embedding_vector=content_data.embedding_vector,
                            extra_metadata=content_data.extra_metadata,
                        )
                    )

                # Combine abstract chunks if found
                if abstract_chunks:
                    abstract_content = " ".join(abstract_chunks).strip()
                    # Clean up the abstract (remove extra whitespace)
                    abstract_content = " ".join(abstract_content.split())
                    if abstract_content and not paper_orm.abstract:
                        # Only update if paper doesn't already have an abstract
                        paper_orm.abstract = abstract_content
                        logger.info(
                            "Extracted abstract from parsed content for paper '%s' (length: %d)",
                            paper_orm.id,
                            len(abstract_content),
                        )

                session.add_all(content_objects)
                paper_orm.parsed = True
                await session.commit()
                await session.refresh(paper_orm, ["contents"])

                logger.info(
                    "Successfully parsed %d sections for paper '%s'",
                    len(content_objects),
                    paper_orm.id,
                )

                # Schedule background task to generate embeddings and store in Zilliz
                background_tasks.add_task(
                    embedding_service.embed_paper_chunks,
                    paper_orm.id,
                )
                logger.debug("Scheduled embedding task for paper '%s'", paper_orm.id)
        except Exception as e:
            logger.exception(
                "Failed to parse PDF content for paper '%s': %s",
                paper_orm.id,
                str(e),
            )
            # Continue even if parsing fails - paper is still created

        logger.info(
            "Successfully created paper '%s' with ID '%s' from uploaded PDF",
            final_metadata["title"],
            paper_orm.id,
        )

        return CreateResponse(
            success=True,
            message="Paper successfully uploaded and created",
            created_count=1,
            created_ids=[str(paper_orm.id)],
        )

    except Exception as e:
        # Clean up file if paper creation failed
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass

        logger.exception(
            "Failed to upload and create paper from file '%s': %s",
            file.filename,
            str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to upload paper: {e}"
        ) from e


@router.get("", response_model=list[PaperResponse])
async def get_papers(
    session: SessionDep,
) -> Any:
    """
    List all papers from Postgres.
    """
    logger.debug("Retrieving all papers")
    papers_orm = await paper_db.get_papers(session)
    return [PaperResponse.from_orm_with_collections(paper) for paper in papers_orm]


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(session: SessionDep, paper_id: str) -> Any:
    """
    Get a specific paper from Postgres.
    """
    logger.debug("Retrieving paper with ID '%s'", paper_id)
    try:
        paper_uuid = UUID(paper_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid paper ID format") from e

    paper_orm = await paper_db.get_paper_by_id(session, paper_uuid)
    if not paper_orm:
        logger.warning("Paper '%s' not found", paper_id)
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperResponse.from_orm_with_collections(paper_orm)


@router.patch("/{paper_id}", response_model=UpdateResponse)
async def update_paper(
    session: SessionDep,
    paper_id: str,
    paper: PaperUpdate,
) -> Any:
    """
    Update a paper in Postgres.
    """
    logger.debug("Updating paper '%s'", paper_id)
    try:
        paper_uuid = UUID(paper_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid paper ID format") from e

    updated = await paper_db.update_paper(session, paper_uuid, paper)
    if not updated:
        raise HTTPException(status_code=404, detail="Paper not found")

    return UpdateResponse(
        success=True,
        message="Paper successfully updated",
        matched_count=1,
        modified_count=1,
    )


@router.delete("/{paper_id}", response_model=DeleteResponse)
async def delete_paper(session: SessionDep, paper_id: str) -> Any:
    """
    Delete a paper from Postgres.
    """
    logger.debug("Deleting paper '%s'", paper_id)
    try:
        paper_uuid = UUID(paper_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid paper ID format") from e

    deleted = await paper_db.delete_paper(session, paper_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Paper not found")

    return DeleteResponse(
        success=True,
        message="Paper successfully deleted",
        deleted_count=1,
    )


@router.get("/by-job/{job_id}", response_model=list[PaperResponse])
async def get_papers_by_job(
    session: SessionDep,
    job_id: str,
) -> Any:
    """
    Get all papers created by a specific crawler job.
    """
    logger.debug("Retrieving papers for job '%s'", job_id)
    try:
        job_uuid = UUID(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid job ID format") from e

    papers_orm = await paper_db.get_papers_by_job_id(session, job_uuid)
    return [PaperResponse.from_orm_with_collections(paper) for paper in papers_orm]


@router.get("/analytics/papers-per-month", response_model=list[dict[str, int]])
async def get_papers_per_month(
    session: SessionDep,
    year: int | None = None,
) -> Any:
    """
    Get count of papers per month for analytics.
    Returns list of dicts with 'month' (1-12) and 'papers' (count).
    """
    logger.debug("Retrieving papers per month analytics for year=%s", year)
    result = await paper_db.get_papers_per_month(session, year=year)
    return result
