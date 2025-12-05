import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.types import JobStatus, PaperSource, Role


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversation"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Message(Base):
    __tablename__ = "message"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment",
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Attachment(Base):
    __tablename__ = "attachment"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    message: Mapped["Message"] = relationship("Message", back_populates="attachments")


# Composite indexes
Index("ix_message_conversation_created_at", Message.conversation_id, Message.created_at)
Index("ix_attachment_message_created_at", Attachment.message_id, Attachment.created_at)


class Paper(Base):
    __tablename__ = "paper"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)

    authors: Mapped[list[str]] = mapped_column(JSONB, nullable=True)

    year: Mapped[int] = mapped_column(Integer, nullable=True)

    venue: Mapped[str] = mapped_column(String(255), nullable=True)

    abstract: Mapped[str] = mapped_column(Text, nullable=True)

    source_type: Mapped[str] = mapped_column(Enum("upload", "url", name="source_type"), nullable=False)

    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional reference to the crawler job that produced this paper
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawler_job.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    parsed: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    contents: Mapped[list["PaperContent"]] = relationship(
        "PaperContent",
        back_populates="paper",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    collections: Mapped[list["Collection"]] = relationship(
        "Collection",
        secondary="paper_collection",
        back_populates="papers",
    )


class PaperContent(Base):
    __tablename__ = "paper_content"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section_name: Mapped[str] = mapped_column(String(255), nullable=False)

    section_index: Mapped[int] = mapped_column(Integer, nullable=True)

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    token_count: Mapped[int] = mapped_column(Integer, nullable=True)

    embedding_vector: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)  # vector embedding

    extra_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    paper: Mapped["Paper"] = relationship("Paper", back_populates="contents")


# Composite index for retrieval efficiency
Index("ix_papercontent_paper_section_chunk", PaperContent.paper_id, PaperContent.section_index, PaperContent.chunk_index)


class CrawlerConfig(Base):
    __tablename__ = "crawler_config"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    source: Mapped[PaperSource] = mapped_column(
        Enum(PaperSource),
        nullable=False
    )

    rate_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    max_delay: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    max_concurrent: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    output_dir: Mapped[str] = mapped_column(String(512), default="crawled_papers", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class CrawlerJob(Base):
    __tablename__ = "crawler_job"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    config_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    urls: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    query: Mapped[str | None] = mapped_column(Text, nullable=True)

    max_papers: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
        index=True
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


# Association table for many-to-many relationship between Paper and Collection
paper_collection = Table(
    "paper_collection",
    Base.metadata,
    Column("paper_id", UUID(as_uuid=True), ForeignKey("paper.id", ondelete="CASCADE"), primary_key=True),
    Column("collection_id", UUID(as_uuid=True), ForeignKey("collection.id", ondelete="CASCADE"), primary_key=True),
)


class Collection(Base):
    __tablename__ = "collection"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    papers: Mapped[list["Paper"]] = relationship(
        "Paper",
        secondary="paper_collection",
        back_populates="collections",
    )
