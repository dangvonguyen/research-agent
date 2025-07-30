import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.models import Paper, PaperCreate, PaperUpdate
from app.repos import PaperRepository

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=Paper)
async def create_paper(paper: PaperCreate) -> Any:
    """
    Create a new paper.
    """
    logger.info(
        "Creating new paper '%s' for source '%s'",
        paper.source_id, paper.source.value,
    )
    result = await PaperRepository.create(paper)
    logger.debug(
        "Successfully created paper '%s' with ID '%s'",
        paper.source_id, result.id,
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
    papers = await PaperRepository.list(skip, limit)
    logger.debug("Found %d papers", len(papers))
    return papers


@router.get("/{paper_id}", response_model=Paper)
async def get_paper(paper_id: str) -> Any:
    """
    Get a specific paper.
    """
    logger.debug("Retrieving paper with ID '%s'", paper_id)
    paper = await PaperRepository.get(paper_id)
    if not paper:
        logger.warning("Paper '%s' not found", paper_id)
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.patch("/{paper_id}", response_model=Paper)
async def update_paper(paper_id: str, paper: PaperUpdate) -> Any:
    """
    Update a paper.
    """
    logger.info("Updating paper '%s'", paper_id)
    logger.debug("Update data: %s", paper.model_dump(mode="json", exclude_unset=True))

    updated_paper = await PaperRepository.update(paper_id, paper)
    if not updated_paper:
        logger.warning("Paper '%s' not found for update", paper_id)
        raise HTTPException(status_code=404, detail="Paper not found")

    logger.info("Successfully updated paper '%s'", paper_id)
    return updated_paper


@router.delete("/{paper_id}", response_model=bool)
async def delete_paper(paper_id: str) -> Any:
    """
    Delete a paper.
    """
    logger.info("Deleting paper '%s'", paper_id)
    success = await PaperRepository.delete(paper_id)
    if not success:
        logger.warning("Paper '%s' not found for deletion", paper_id)
        raise HTTPException(status_code=404, detail="Paper not found")

    logger.info("Successfully deleted paper '%s'", paper_id)
    return success
