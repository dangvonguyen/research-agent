from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Collection, Paper, paper_collection
from app.types import CollectionCreate, CollectionUpdate


async def create_collection(
    session: AsyncSession, collection: CollectionCreate
) -> Collection:
    """
    Create a new collection.
    """
    collection_dict = collection.model_dump(exclude_unset=True)
    collection_orm = Collection(**collection_dict)
    session.add(collection_orm)
    await session.commit()
    await session.refresh(collection_orm)
    return collection_orm


async def get_collections(
    session: AsyncSession
) -> list[tuple[Collection, int]]:
    """
    Get all collections with paper counts.
    Returns list of tuples (collection, paper_count).
    """
    stmt = select(Collection).order_by(Collection.updated_at.desc())
    result = await session.execute(stmt)
    collections = result.scalars().all()
    
    # Get paper counts for each collection
    collections_with_counts = []
    for collection in collections:
        count_stmt = select(func.count(paper_collection.c.paper_id)).where(
            paper_collection.c.collection_id == collection.id
        )
        count_result = await session.execute(count_stmt)
        paper_count = count_result.scalar() or 0
        collections_with_counts.append((collection, paper_count))
    
    return collections_with_counts


async def get_collection_by_id(
    session: AsyncSession, collection_id: UUID
) -> tuple[Collection | None, int]:
    """
    Get a collection by ID with papers loaded.
    Returns tuple (collection, paper_count).
    """
    stmt = (
        select(Collection)
        .where(Collection.id == collection_id)
        .options(selectinload(Collection.papers))
    )
    result = await session.execute(stmt)
    collection = result.scalar_one_or_none()
    
    if not collection:
        return None, 0
    
    # Get paper count
    count_stmt = select(func.count(paper_collection.c.paper_id)).where(
        paper_collection.c.collection_id == collection.id
    )
    count_result = await session.execute(count_stmt)
    paper_count = count_result.scalar() or 0
    
    return collection, paper_count


async def update_collection(
    session: AsyncSession, collection_id: UUID, collection: CollectionUpdate
) -> Collection | None:
    """
    Update a collection.
    """
    stmt = select(Collection).where(Collection.id == collection_id)
    result = await session.execute(stmt)
    collection_orm = result.scalar_one_or_none()
    
    if not collection_orm:
        return None
    
    update_data = collection.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(collection_orm, key, value)
    
    await session.commit()
    await session.refresh(collection_orm)
    return collection_orm


async def delete_collection(
    session: AsyncSession, collection_id: UUID
) -> bool:
    """
    Delete a collection.
    """
    stmt = select(Collection).where(Collection.id == collection_id)
    result = await session.execute(stmt)
    collection_orm = result.scalar_one_or_none()
    
    if not collection_orm:
        return False
    
    await session.delete(collection_orm)
    await session.commit()
    return True


async def add_paper_to_collection(
    session: AsyncSession, collection_id: UUID, paper_id: UUID
) -> bool:
    """
    Add a paper to a collection.
    """
    # Check if both exist
    collection_stmt = select(Collection).where(Collection.id == collection_id)
    collection_result = await session.execute(collection_stmt)
    collection = collection_result.scalar_one_or_none()
    
    paper_stmt = select(Paper).where(Paper.id == paper_id)
    paper_result = await session.execute(paper_stmt)
    paper = paper_result.scalar_one_or_none()
    
    if not collection or not paper:
        return False
    
    # Check if association already exists
    check_stmt = select(paper_collection).where(
        paper_collection.c.collection_id == collection_id,
        paper_collection.c.paper_id == paper_id,
    )
    check_result = await session.execute(check_stmt)
    if check_result.first():
        return True  # Already exists
    
    # Create association
    insert_stmt = paper_collection.insert().values(
        collection_id=collection_id, paper_id=paper_id
    )
    await session.execute(insert_stmt)
    await session.commit()
    return True


async def remove_paper_from_collection(
    session: AsyncSession, collection_id: UUID, paper_id: UUID
) -> bool:
    """
    Remove a paper from a collection.
    """
    delete_stmt = paper_collection.delete().where(
        paper_collection.c.collection_id == collection_id,
        paper_collection.c.paper_id == paper_id,
    )
    result = await session.execute(delete_stmt)
    await session.commit()
    return result.rowcount > 0


async def get_papers_in_collection(
    session: AsyncSession, collection_id: UUID
) -> list[Paper]:
    """
    Get all papers in a collection with contents and collections loaded.
    """
    stmt = (
        select(Paper)
        .join(paper_collection, Paper.id == paper_collection.c.paper_id)
        .where(paper_collection.c.collection_id == collection_id)
        .options(
            selectinload(Paper.contents),
            selectinload(Paper.collections)
        )
        .order_by(Paper.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_collection_paper_count(
    session: AsyncSession, collection_id: UUID
) -> int:
    """
    Get the count of papers in a collection.
    """
    stmt = select(func.count(paper_collection.c.paper_id)).where(
        paper_collection.c.collection_id == collection_id
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def get_papers_by_collection(
    session: AsyncSession
) -> list[dict[str, Any]]:
    """
    Get count of papers per collection.
    Returns list of dicts with 'name' (collection name) and 'value' (paper count).
    """
    stmt = (
        select(
            Collection.name,
            func.count(paper_collection.c.paper_id).label('count')
        )
        .outerjoin(paper_collection, Collection.id == paper_collection.c.collection_id)
        .group_by(Collection.id, Collection.name)
        .order_by(func.count(paper_collection.c.paper_id).desc())
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    return [
        {'name': row.name, 'value': int(row.count) if row.count else 0}
        for row in rows
        if row.count and row.count > 0  # Only include collections with papers
    ]
