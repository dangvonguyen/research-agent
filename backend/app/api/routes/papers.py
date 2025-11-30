import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep
from app.db.queries import paper as paper_db
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


@router.post("", response_model=CreateResponse)
async def create_paper(session: SessionDep, paper: PaperCreate) -> Any:
    """
    Create a new paper stored in Postgres.
    """
    logger.info(
        "Creating new paper '%s' for source '%s'",
        paper.source_id,
        paper.source.value,
    )
    result = await paper_db.create_paper(session, paper)
    logger.info(
        "Successfully created paper '%s' with ID '%s'",
        paper.source_id,
        result.id,
    )
    return CreateResponse(
        success=True,
        message="Paper successfully created",
        created_count=1,
        created_ids=[str(result.id)],
    )


@router.get("", response_model=list[PaperResponse])
async def get_papers(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    List all papers from Postgres.
    """
    logger.debug("Retrieving papers with skip=%d, limit=%d", skip, limit)
    papers_orm = await paper_db.get_papers(session, skip=skip, limit=limit)
    return [PaperResponse.model_validate(paper) for paper in papers_orm]


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(session: SessionDep, paper_id: str) -> Any:
    """
    Get a specific paper from Postgres.
    """
    logger.debug("Retrieving paper with ID '%s'", paper_id)
    try:
        paper_uuid = UUID(paper_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid paper ID format")

    paper_orm = await paper_db.get_paper_by_id(session, paper_uuid)
    if not paper_orm:
        logger.warning("Paper '%s' not found", paper_id)
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperResponse.model_validate(paper_orm)


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
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid paper ID format")

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
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid paper ID format")

    deleted = await paper_db.delete_paper(session, paper_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Paper not found")

    return DeleteResponse(
        success=True,
        message="Paper successfully deleted",
        deleted_count=1,
    )
