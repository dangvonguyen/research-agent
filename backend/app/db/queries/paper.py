from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Paper, PaperContent as PaperContentORM
from app.types import PaperCreate, PaperContent, PaperUpdate


async def create_paper(
    session: AsyncSession, paper: Paper | PaperCreate, job_id: UUID | None = None
) -> Paper:
    """
    Create a new paper with its content sections.

    Accepts either a Pydantic PaperCreate (API layer) or an ORM Paper (crawler layer).
    """
    # If we already have an ORM Paper instance (e.g. from crawler), just attach job_id and persist
    if isinstance(paper, Paper):
        if job_id is not None:
            paper.job_id = job_id
        session.add(paper)
        await session.commit()
        await session.refresh(paper, ["contents"])
        return paper

    # Otherwise handle the API schema PaperCreate and map it into the ORM Paper model
    # PaperBase now matches database structure, so we can use it directly
    paper_dict = paper.model_dump(
        exclude_unset=True,
        exclude={"contents", "job_id"},
    )

    # Set parsed to False initially
    paper_dict["parsed"] = False

    # Set job_id if provided (from crawler job or paper.job_id)
    if job_id is not None:
        paper_dict["job_id"] = job_id
    elif paper.job_id:
        try:
            # Check if job_id is already a UUID object (from asyncpg or Python UUID)
            if isinstance(paper.job_id, UUID):
                paper_dict["job_id"] = paper.job_id
            elif hasattr(paper.job_id, '__str__'):
                # Handle asyncpg UUID or other UUID-like objects
                # Convert to string first, then to Python UUID
                paper_dict["job_id"] = UUID(str(paper.job_id))
            else:
                # Try direct conversion for string
                paper_dict["job_id"] = UUID(paper.job_id)
        except (ValueError, TypeError, AttributeError):
            pass

    # Create the paper
    paper_db = Paper(**paper_dict)
    session.add(paper_db)
    await session.flush()  # Flush to get the paper ID

    # Create PaperContent entries from contents
    if paper.contents:
        content_objects = []
        section_index = 0
        for content_data in paper.contents:
            if isinstance(content_data, PaperContent):
                content_objects.append(
                    PaperContentORM(
                        paper_id=paper_db.id,
                        section_name=content_data.section_name,
                        section_index=content_data.section_index or section_index,
                        chunk_index=content_data.chunk_index or 0,
                        content=content_data.content,
                        token_count=content_data.token_count,
                        embedding_vector=content_data.embedding_vector,
                        extra_metadata=content_data.extra_metadata,
                    )
                )
                section_index += 1
            elif isinstance(content_data, dict):
                # Handle dict format
                content_objects.append(
                    PaperContentORM(
                        paper_id=paper_db.id,
                        section_name=content_data.get("section_name", ""),
                        section_index=content_data.get("section_index", section_index),
                        chunk_index=content_data.get("chunk_index", 0),
                        content=content_data.get("content", ""),
                        token_count=content_data.get("token_count"),
                        embedding_vector=content_data.get("embedding_vector"),
                        extra_metadata=content_data.get("extra_metadata"),
                    )
                )
                section_index += 1

        if content_objects:
            session.add_all(content_objects)

    await session.commit()
    await session.refresh(paper_db, ["contents"])
    return paper_db


async def create_papers(
    session: AsyncSession, papers: list[Paper | PaperCreate], job_id: UUID | None = None
) -> list[Paper]:
    """Create multiple papers with their content sections."""
    created_papers: list[Paper] = []
    for paper in papers:
        created_paper = await create_paper(session, paper, job_id)
        created_papers.append(created_paper)
    return created_papers


async def get_papers(
    session: AsyncSession, skip: int | None = None, limit: int | None = None
) -> list[Paper]:
    """Get all papers with contents and collections loaded."""
    stmt = (
        select(Paper)
        .options(
            selectinload(Paper.contents),
            selectinload(Paper.collections)
        )
        .order_by(Paper.created_at.desc())
    )
    if skip is not None:
        stmt = stmt.offset(skip)
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_paper_by_id(
    session: AsyncSession, paper_id: UUID
) -> Paper | None:
    """Get a paper by ID with its contents and collections."""
    stmt = (
        select(Paper)
        .options(
            selectinload(Paper.contents),
            selectinload(Paper.collections)
        )
        .where(Paper.id == paper_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_paper(
    session: AsyncSession, paper_id: UUID, update_data: PaperUpdate
) -> Paper | None:
    """Update a paper."""
    stmt = select(Paper).where(Paper.id == paper_id)
    result = await session.execute(stmt)
    paper = result.scalar_one_or_none()
    if not paper:
        return None

    # PaperUpdate now matches database structure, so we can use it directly
    update_dict = update_data.model_dump(exclude_unset=True, exclude={"contents"})
    
    for key, value in update_dict.items():
        setattr(paper, key, value)

    # Update contents if provided
    if update_data.contents:
        # Delete existing contents
        existing_contents = await get_paper_contents_by_paper_id(session, paper_id)
        for content in existing_contents:
            await session.delete(content)
        await session.flush()

        # Create new PaperContent entries from contents
        content_objects = []
        section_index = 0
        for content_data in update_data.contents:
            if isinstance(content_data, PaperContent):
                content_objects.append(
                    PaperContentORM(
                        paper_id=paper_id,
                        section_name=content_data.section_name,
                        section_index=content_data.section_index or section_index,
                        chunk_index=content_data.chunk_index or 0,
                        content=content_data.content,
                        token_count=content_data.token_count,
                        embedding_vector=content_data.embedding_vector,
                        extra_metadata=content_data.extra_metadata,
                    )
                )
                section_index += 1
            elif isinstance(content_data, dict):
                content_objects.append(
                    PaperContentORM(
                        paper_id=paper_id,
                        section_name=content_data.get("section_name", ""),
                        section_index=content_data.get("section_index", section_index),
                        chunk_index=content_data.get("chunk_index", 0),
                        content=content_data.get("content", ""),
                        token_count=content_data.get("token_count"),
                        embedding_vector=content_data.get("embedding_vector"),
                        extra_metadata=content_data.get("extra_metadata"),
                    )
                )
                section_index += 1
        
        if content_objects:
            session.add_all(content_objects)
            paper.parsed = True  # Mark as parsed when contents are added

    await session.commit()
    await session.refresh(paper, ["contents"])
    return paper


async def delete_paper(session: AsyncSession, paper_id: UUID) -> bool:
    """Delete a paper (contents will be deleted via CASCADE)."""
    stmt = select(Paper).where(Paper.id == paper_id)
    result = await session.execute(stmt)
    paper = result.scalar_one_or_none()
    if not paper:
        return False

    await session.delete(paper)
    await session.commit()
    return True


async def get_paper_contents_by_paper_id(
    session: AsyncSession, paper_id: UUID
) -> list[PaperContent]:
    """Get all content sections for a paper."""
    stmt = (
        select(PaperContent)
        .where(PaperContent.paper_id == paper_id)
        .order_by(PaperContent.section_index, PaperContent.chunk_index)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_papers_by_job_id(
    session: AsyncSession, job_id: UUID
) -> list[Paper]:
    """Get all papers created by a specific job with contents and collections loaded."""
    stmt = (
        select(Paper)
        .where(Paper.job_id == job_id)
        .options(
            selectinload(Paper.contents),
            selectinload(Paper.collections)
        )
        .order_by(Paper.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_papers_per_month(
    session: AsyncSession, year: int | None = None
) -> list[dict[str, int]]:
    """
    Get count of papers per month.
    Returns list of dicts with 'month' (1-12) and 'papers' (count).
    If year is None, uses current year.
    """
    if year is None:
        year = datetime.now().year
    
    # Query papers grouped by month
    stmt = (
        select(
            extract('month', Paper.created_at).label('month'),
            func.count(Paper.id).label('count')
        )
        .where(extract('year', Paper.created_at) == year)
        .group_by(extract('month', Paper.created_at))
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    # Create a dict with all months initialized to 0
    month_data = {i: 0 for i in range(1, 13)}
    for row in rows:
        month_data[int(row.month)] = int(row.count)
    
    # Convert to list of dicts
    return [
        {'month': month, 'papers': month_data[month]}
        for month in range(1, 13)
    ]

