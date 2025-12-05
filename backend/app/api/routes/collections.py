import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep
from app.db.queries import collection as collection_db
from app.types import (
    CollectionCreate,
    CollectionResponse,
    CollectionUpdate,
    CreateResponse,
    DeleteResponse,
    PaperResponse,
    UpdateResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=CreateResponse)
async def create_collection(session: SessionDep, collection: CollectionCreate) -> Any:
    """
    Create a new collection.
    """
    logger.info("Creating new collection '%s'", collection.name)
    result = await collection_db.create_collection(session, collection)
    logger.info("Successfully created collection '%s' with ID '%s'", collection.name, result.id)
    return CreateResponse(
        success=True,
        message="Collection successfully created",
        created_count=1,
        created_ids=[str(result.id)],
    )


@router.get("", response_model=list[CollectionResponse])
async def get_collections(
    session: SessionDep,
) -> Any:
    """
    List all collections.
    """
    logger.debug("Retrieving all collections")
    collections_with_counts = await collection_db.get_collections(session)
    return [
        CollectionResponse(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            paper_count=paper_count,
        )
        for collection, paper_count in collections_with_counts
    ]


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(session: SessionDep, collection_id: str) -> Any:
    """
    Get a specific collection.
    """
    logger.debug("Retrieving collection with ID '%s'", collection_id)
    try:
        collection_uuid = UUID(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID format")

    collection_orm, paper_count = await collection_db.get_collection_by_id(session, collection_uuid)
    if not collection_orm:
        logger.warning("Collection '%s' not found", collection_id)
        raise HTTPException(status_code=404, detail="Collection not found")
    
    return CollectionResponse(
        id=collection_orm.id,
        name=collection_orm.name,
        description=collection_orm.description,
        created_at=collection_orm.created_at,
        updated_at=collection_orm.updated_at,
        paper_count=paper_count,
    )


@router.patch("/{collection_id}", response_model=UpdateResponse)
async def update_collection(
    session: SessionDep,
    collection_id: str,
    collection: CollectionUpdate,
) -> Any:
    """
    Update a collection.
    """
    logger.debug("Updating collection '%s'", collection_id)
    try:
        collection_uuid = UUID(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID format")

    updated = await collection_db.update_collection(session, collection_uuid, collection)
    if not updated:
        raise HTTPException(status_code=404, detail="Collection not found")

    return UpdateResponse(
        success=True,
        message="Collection successfully updated",
        matched_count=1,
        modified_count=1,
    )


@router.delete("/{collection_id}", response_model=DeleteResponse)
async def delete_collection(session: SessionDep, collection_id: str) -> Any:
    """
    Delete a collection.
    """
    logger.debug("Deleting collection '%s'", collection_id)
    try:
        collection_uuid = UUID(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID format")

    deleted = await collection_db.delete_collection(session, collection_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Collection not found")

    return DeleteResponse(
        success=True,
        message="Collection successfully deleted",
        deleted_count=1,
    )


@router.get("/{collection_id}/papers", response_model=list[PaperResponse])
async def get_collection_papers(
    session: SessionDep,
    collection_id: str,
) -> Any:
    """
    Get all papers in a collection.
    """
    logger.debug("Retrieving all papers for collection '%s'", collection_id)
    try:
        collection_uuid = UUID(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID format")

    # Verify collection exists
    collection_orm, _ = await collection_db.get_collection_by_id(session, collection_uuid)
    if not collection_orm:
        raise HTTPException(status_code=404, detail="Collection not found")

    papers_orm = await collection_db.get_papers_in_collection(
        session, collection_uuid
    )
    return [PaperResponse.from_orm_with_collections(paper) for paper in papers_orm]


@router.post("/{collection_id}/papers/{paper_id}", response_model=UpdateResponse)
async def add_paper_to_collection(
    session: SessionDep,
    collection_id: str,
    paper_id: str,
) -> Any:
    """
    Add a paper to a collection.
    """
    logger.debug("Adding paper '%s' to collection '%s'", paper_id, collection_id)
    try:
        collection_uuid = UUID(collection_id)
        paper_uuid = UUID(paper_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    success = await collection_db.add_paper_to_collection(
        session, collection_uuid, paper_uuid
    )
    if not success:
        raise HTTPException(
            status_code=404, detail="Collection or paper not found, or already added"
        )

    return UpdateResponse(
        success=True,
        message="Paper successfully added to collection",
        matched_count=1,
        modified_count=1,
    )


@router.delete("/{collection_id}/papers/{paper_id}", response_model=UpdateResponse)
async def remove_paper_from_collection(
    session: SessionDep,
    collection_id: str,
    paper_id: str,
) -> Any:
    """
    Remove a paper from a collection.
    """
    logger.debug("Removing paper '%s' from collection '%s'", paper_id, collection_id)
    try:
        collection_uuid = UUID(collection_id)
        paper_uuid = UUID(paper_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    success = await collection_db.remove_paper_from_collection(
        session, collection_uuid, paper_uuid
    )
    if not success:
        raise HTTPException(
            status_code=404, detail="Paper not found in collection"
        )

    return UpdateResponse(
        success=True,
        message="Paper successfully removed from collection",
        matched_count=1,
        modified_count=1,
    )


@router.get("/analytics/papers-by-collection", response_model=list[dict[str, Any]])
async def get_papers_by_collection(session: SessionDep) -> Any:
    """
    Get count of papers per collection for analytics.
    Returns list of dicts with 'name' (collection name) and 'value' (paper count).
    """
    logger.debug("Retrieving papers by collection analytics")
    result = await collection_db.get_papers_by_collection(session)
    return result
