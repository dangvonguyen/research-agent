from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Paper, PaperContent
from app.types import PaperCreate, PaperSection, PaperUpdate


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
    paper_dict = paper.model_dump(
        exclude_unset=True,
        exclude={
            "sections",
            "source",
            "source_id",
            "url",
            "pdf_url",
            "local_pdf_path",
            "venues",
            "job_id",
        },
    )

    # Map source and URLs
    if paper.url or paper.pdf_url:
        paper_dict["source_type"] = "url"
        paper_dict["source_url"] = paper.url or paper.pdf_url
    else:
        paper_dict["source_type"] = "upload"
        paper_dict["source_url"] = None

    # Map file path
    paper_dict["file_path"] = paper.local_pdf_path

    # Map venue (take first venue if multiple)
    if paper.venues:
        paper_dict["venue"] = paper.venues[0] if paper.venues else None

    # Set parsed to False initially
    paper_dict["parsed"] = False

    # Set job_id if provided (from crawler job or paper.job_id)
    if job_id is not None:
        paper_dict["job_id"] = job_id
    elif paper.job_id:
        try:
            paper_dict["job_id"] = UUID(paper.job_id)
        except (ValueError, TypeError):
            pass

    # Create the paper
    paper_db = Paper(**paper_dict)
    session.add(paper_db)
    await session.flush()  # Flush to get the paper ID

    # Create PaperContent entries from sections
    if paper.sections:
        content_objects = []
        section_index = 0
        for section_name, section_data in paper.sections.items():
            if isinstance(section_data, PaperSection):
                content_objects.append(
                    PaperContent(
                        paper_id=paper_db.id,
                        section_name=section_data.title or section_name,
                        section_index=section_index,
                        chunk_index=0,  # Default to 0, can be updated later
                        content=section_data.content,
                        token_count=None,  # Can be calculated later
                        embedding_vector=None,
                        extra_metadata={
                            "level": section_data.level
                        }
                        if section_data.level
                        else None,
                    )
                )
                section_index += 1
            elif isinstance(section_data, dict):
                # Handle dict format
                content_objects.append(
                    PaperContent(
                        paper_id=paper_db.id,
                        section_name=section_data.get("title", section_name),
                        section_index=section_index,
                        chunk_index=0,
                        content=section_data.get("content", ""),
                        token_count=None,
                        embedding_vector=None,
                        extra_metadata={
                            "level": section_data.get("level", 1)
                        },
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
    session: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Paper]:
    """Get all papers."""
    stmt = (
        select(Paper)
        .options(selectinload(Paper.contents))
        .offset(skip)
        .limit(limit)
        .order_by(Paper.updated_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_paper_by_id(
    session: AsyncSession, paper_id: UUID
) -> Paper | None:
    """Get a paper by ID with its contents."""
    stmt = (
        select(Paper)
        .options(selectinload(Paper.contents))
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

    update_dict = update_data.model_dump(exclude_unset=True, exclude={"sections", "source", "source_id", "url", "pdf_url", "local_pdf_path", "venues"})
    
    # Map source and URLs if provided
    if update_data.url or update_data.pdf_url:
        update_dict["source_type"] = "url"
        update_dict["source_url"] = update_data.url or update_data.pdf_url
    elif update_data.local_pdf_path:
        update_dict["source_type"] = "upload"
        update_dict["file_path"] = update_data.local_pdf_path
    
    # Map venue
    if update_data.venues:
        update_dict["venue"] = update_data.venues[0] if update_data.venues else None
    
    for key, value in update_dict.items():
        setattr(paper, key, value)

    # Update sections if provided
    if update_data.sections:
        # Delete existing contents
        existing_contents = await get_paper_contents_by_paper_id(session, paper_id)
        for content in existing_contents:
            await session.delete(content)
        await session.flush()

        # Create new PaperContent entries from sections
        content_objects = []
        section_index = 0
        for section_name, section_data in update_data.sections.items():
            if isinstance(section_data, PaperSection):
                content_objects.append(
                    PaperContent(
                        paper_id=paper_id,
                        section_name=section_data.title or section_name,
                        section_index=section_index,
                        chunk_index=0,
                        content=section_data.content,
                        token_count=None,
                        embedding_vector=None,
                        extra_metadata={"level": section_data.level} if section_data.level else None,
                    )
                )
                section_index += 1
            elif isinstance(section_data, dict):
                content_objects.append(
                    PaperContent(
                        paper_id=paper_id,
                        section_name=section_data.get("title", section_name),
                        section_index=section_index,
                        chunk_index=0,
                        content=section_data.get("content", ""),
                        token_count=None,
                        embedding_vector=None,
                        extra_metadata={"level": section_data.get("level", 1)},
                    )
                )
                section_index += 1
        
        if content_objects:
            session.add_all(content_objects)
            paper.parsed = True  # Mark as parsed when sections are added

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

