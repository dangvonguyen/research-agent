import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.models import (
    CreateResponse,
    DeleteResponse,
    Paper,
    PaperCreate,
    PaperUpdate,
    UpdateResponse,
)
from app.repos import PaperRepository

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=CreateResponse)
async def create_paper(paper: PaperCreate) -> Any:
    """
    Create a new paper.
    """
    logger.info(
        "Creating new paper '%s' for source '%s'",
        paper.source_id, paper.source.value,
    )
    result = await PaperRepository.create_one(paper)
    logger.info(
        "Successfully created paper '%s' with ID '%s'",
        paper.source_id, result.created_ids[0],
    )
    return result


@router.get("", response_model=list[Paper])
async def get_papers(skip: int = 0, limit: int = 100) -> Any:
    """
    List all papers.
    """
    logger.debug(
        "Retrieving papers with skip=%d, limit=%d", skip, limit
    )
    return await PaperRepository.get_many(skip=skip, limit=limit)


@router.get("/{paper_id}", response_model=Paper)
async def get_paper(paper_id: str) -> Any:
    """
    Get a specific paper.
    """
    logger.debug("Retrieving paper with ID '%s'", paper_id)
    paper = await PaperRepository.get_by_id(paper_id)
    if not paper:
        logger.warning("Paper '%s' not found", paper_id)
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.patch("/{paper_id}", response_model=UpdateResponse)
async def update_paper(paper_id: str, paper: PaperUpdate) -> Any:
    """
    Update a paper.
    """
    logger.debug("Updating paper '%s'", paper_id)
    return await PaperRepository.update_by_id(paper_id, paper)


@router.delete("/{paper_id}", response_model=DeleteResponse)
async def delete_paper(paper_id: str) -> Any:
    """
    Delete a paper.
    """
    logger.debug("Deleting paper '%s'", paper_id)
    return await PaperRepository.delete_by_id(paper_id)
