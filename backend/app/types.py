from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class PaperSource(Enum):
    """Source of a paper."""

    ACL_ANTHOLOGY = "acl_anthology"


class Role(str, Enum):
    """Role of a message sender."""

    USER = "user"
    ASSISTANT = "assistant"


class JobStatus(Enum):
    """Status of processing a job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseCreate(BaseModel):
    """Base model for all create operations."""

    pass


class BaseUpdate(BaseModel):
    """Base model for all update operations."""

    pass


class BaseDocument(BaseModel):
    """Base model for all database documents."""

    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
    }


class CrawlerConfigBase(BaseModel):
    """Base model for crawler configurations."""

    name: str
    source: PaperSource
    rate_limit: int = Field(default=10, ge=1)
    max_delay: int = Field(default=60, ge=1)
    max_attempts: int = Field(default=3, ge=1)
    max_concurrent: int = Field(default=10, ge=1)
    output_dir: str = "crawled_papers"


class CrawlerConfigCreate(BaseCreate, CrawlerConfigBase):
    """Model for creating a new crawler configuration."""

    pass


class CrawlerConfigUpdate(BaseUpdate):
    """Model for updating an existing crawler configuration."""

    name: str | None = None
    source: PaperSource | None = None
    rate_limit: int | None = None
    max_delay: int | None = None
    max_attempts: int | None = None
    max_concurrent: int | None = None
    output_dir: str | None = None


class CrawlerConfig(BaseDocument, CrawlerConfigBase):
    """Model for crawler configuration stored in database."""

    pass


class CrawlerJobBase(BaseModel):
    """Base model for crawler jobs."""

    config_name: str = Field(default="default_acl_anthology")
    urls: list[HttpUrl] | None = None
    max_papers: int | None = Field(default=None, ge=0)


class CrawlerJobCreate(BaseCreate, CrawlerJobBase):
    """Model for creating a new crawler job."""

    pass


class CrawlerJobUpdate(BaseUpdate):
    """Model for updating an existing crawler job."""

    urls: list[HttpUrl] | None = None
    max_papers: int | None = Field(default=None, ge=0)


class CrawlerJob(BaseDocument, CrawlerJobBase):
    """Model for crawler job stored in database."""

    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    status: JobStatus = JobStatus.PENDING


class CrawlerConfigResponse(BaseModel):
    """Response model for crawler configuration from SQLAlchemy."""

    id: UUID
    name: str
    source: PaperSource
    rate_limit: int
    max_delay: int
    max_attempts: int
    max_concurrent: int
    output_dir: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class CrawlerJobResponse(BaseModel):
    """Response model for crawler job from SQLAlchemy."""

    id: UUID
    config_name: str
    urls: list[str] | None = None
    max_papers: int | None = None
    status: JobStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class PaperContent(BaseModel):
    """Model for paper content matching database PaperContent structure."""

    id: UUID
    paper_id: UUID
    section_name: str
    section_index: int | None = None
    chunk_index: int | None = None
    content: str
    token_count: int | None = None
    embedding_vector: list[float] | None = None
    extra_metadata: dict | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class PaperBase(BaseModel):
    """Base model for paper matching database structure (for create/update operations)."""

    title: str
    authors: list[str] | None = None
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    source_type: str  # "url" or "upload"
    source_url: str | None = None
    file_path: str | None = None
    contents: list[PaperContent] = Field(default_factory=list)
    job_id: UUID | None = None


class PaperCreate(BaseCreate, PaperBase):
    """Model for creating a new paper."""

    pass


class PaperUpdate(BaseUpdate):
    """Model for updating an existing paper."""

    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    file_path: str | None = None
    contents: list[PaperContent] | None = None
    job_id: UUID | None = None


class PaperResponse(BaseModel):
    """Response model for paper matching ORM Paper structure (for API responses)."""

    id: UUID
    title: str
    authors: list[str] | None = None
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    source_type: str
    source_url: str | None = None
    file_path: str | None = None
    job_id: UUID | None = None
    parsed: bool
    created_at: datetime
    updated_at: datetime
    contents: list[PaperContent] = Field(default_factory=list)

    model_config = {
        "from_attributes": True,
    }


class Paper(BaseDocument, PaperResponse):
    """Model for paper stored in database (MongoDB)."""

    pass

class OperationResponse(BaseModel):
    """Base response model for database operations."""

    success: bool
    message: str


class CreateResponse(OperationResponse):
    """Response model for create operations."""

    created_count: int
    created_ids: list[str]


class UpdateResponse(OperationResponse):
    """Response model for update operations."""

    matched_count: int
    modified_count: int


class DeleteResponse(OperationResponse):
    """Response model for delete operations."""

    deleted_count: int


class ConversationBase(BaseModel):
    """Base model for conversations."""

    name: str


class ConversationCreate(ConversationBase):
    """Model for creating a new conversation."""

    id: UUID | None = None


class ConversationUpdate(BaseModel):
    """Model for updating an existing conversation."""

    name: str | None = None


class ConversationDB(ConversationBase):
    """Model for conversation stored in database."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


# Message Content Part System
class MessageTextPart(BaseModel):
    """Text content part of a message."""

    type: Literal["text"] = "text"
    text: str


class MessageReasoningPart(BaseModel):
    """Reasoning content part of a message."""

    type: Literal["reasoning"] = "reasoning"
    text: str


class MessageFilePart(BaseModel):
    """File content part of a message."""

    type: Literal["file"] = "file"
    filename: str | None = None
    data: str  # Base64 encoded or URL
    media_type: str


class MessageToolCallPart(BaseModel):
    """Tool call content part of a message."""

    type: Literal["tool-call"] = "tool-call"
    tool_call_id: str
    tool_name: str
    input: dict[str, Any]


class MessageToolResultPart(BaseModel):
    """Tool result content part of a message."""

    type: Literal["tool-result"] = "tool-result"
    tool_call_id: str
    tool_name: str
    output: "ToolResultOutput"


class ToolResultOutput(BaseModel):
    """Result of a tool call. Supports multiple output types."""

    type: Literal["text", "json", "error-text", "error-json", "content"]
    value: Any


# Discriminated union for all content parts
MessageContentPart = (
    MessageTextPart
    | MessageFilePart
    | MessageReasoningPart
    | MessageToolCallPart
    | MessageToolResultPart
)


class Attachment(BaseModel):
    """Model for attachments stored in JSONB."""

    name: str
    path: str
    content_type: str


class MessageBase(BaseModel):
    """Base model for messages."""

    role: Role = Role.USER
    content: list[MessageContentPart]


class MessageCreate(MessageBase):
    """Model for creating a new message."""

    id: UUID | None = None
    attachments: list[Attachment] = Field(default_factory=list)


class MessageUpdate(BaseModel):
    """Model for updating an existing message."""

    content: list[MessageContentPart] | None = None
    role: Role | None = None


class MessageDB(MessageBase):
    """Model for message stored in database."""

    id: UUID
    conversation_id: UUID
    created_at: datetime
    attachments: list[Attachment] = Field(default_factory=list)

    model_config = {
        "from_attributes": True,
    }


class SendMessageRequest(BaseModel):
    """Model for message request."""

    conversation_id: UUID
    message: str | None = None
    attachments: list[dict[str, Any]] | None = None


class StreamEventType(str, Enum):
    """Types of streaming events."""

    CONTENT_START = "content_start"  # New content part is starting
    CONTENT_DELTA = "content_delta"  # Incremental update to content
    CONTENT_END = "content_end"  # Content part is complete
    MESSAGE_END = "message_end"  # Entire message is complete
    ERROR = "error"  # Error occurred
    ABORT = "abort"  # Stream was aborted


class StreamContentType(str, Enum):
    """Types of content that can be streamed."""

    TEXT = "text"
    REASONING = "reasoning"
    TOOL_CALL = "tool-call"
    TOOL_RESULT = "tool-result"


# Base class with shared metadata
class StreamEventBase(BaseModel):
    """Base streaming event with common metadata."""

    conversation_id: UUID
    message_id: UUID
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StreamContentStart(StreamEventBase):
    """Signals the start of a new content part."""

    type: Literal["content_start"] = "content_start"
    content_type: StreamContentType
    index: int  # Position in the content array

    # Tool-specific metadata (only for tool_call/tool_result)
    tool_call_id: str | None = None
    tool_name: str | None = None


class StreamContentDelta(StreamEventBase):
    """Incremental update to a content part."""

    type: Literal["content_delta"] = "content_delta"
    index: int  # Which content part this updates
    delta: str | dict[str, Any]  # Text delta or partial structured data


class StreamContentEnd(StreamEventBase):
    """Signals completion of a content part."""

    type: Literal["content_end"] = "content_end"
    index: int


class StreamMessageEnd(StreamEventBase):
    """Signals completion of entire message."""

    type: Literal["message_end"] = "message_end"


class StreamError(StreamEventBase):
    """Error during streaming."""

    type: Literal["error"] = "error"
    error: str


class StreamAbort(StreamEventBase):
    """Stream was cancelled."""

    type: Literal["abort"] = "abort"
    reason: str = "user_cancelled"


# Discriminated union for all stream events
StreamEvent = (
    StreamContentStart
    | StreamContentDelta
    | StreamContentEnd
    | StreamMessageEnd
    | StreamError
    | StreamAbort
)


# Chat-specific models for AI responses
class ChatRequest(BaseModel):
    """Model for chat request."""

    conversation_id: UUID
    message_id: UUID  # ID of the user message just created


class Response[T](BaseModel):
    """Base model for API responses."""

    data: T
    metadata: dict[str, Any]


class ChatResponse(Response[MessageDB]):
    """Model for chat response model."""

    @classmethod
    def create(
        cls, assistant_data: "MessageDB", conversation_id: UUID
    ) -> "ChatResponse":
        return cls(
            data=assistant_data,
            metadata={
                "conversation_id": conversation_id,
                "message_id": assistant_data.id,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


class StreamChatChunk(Response[StreamEvent]):
    """Model for streaming chat response chunks with typed events."""

    @classmethod
    def create(cls, event: StreamEvent) -> "StreamChatChunk":
        return cls(data=event, metadata={})
