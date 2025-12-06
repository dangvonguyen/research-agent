"""Assembles streaming deltas into complete content parts."""

from typing import Any

from app.types import (
    MessageContentPart,
    MessageReasoningPart,
    MessageTextPart,
    MessageToolCallPart,
    MessageToolResultPart,
    StreamContentType,
)


class ContentPartBuilder:
    """Builds content parts from streaming deltas."""

    def __init__(self) -> None:
        self.parts: list[MessageContentPart | None] = []
        self.current_index: int | None = None
        self.current_type: StreamContentType | None = None
        self.current_data: dict[str, Any] = {}

    def start_content(
        self, content_type: StreamContentType, index: int, **metadata: Any
    ) -> None:
        """Start a new content part."""
        # Finalize previous part if exists
        if self.current_index is not None:
            self._finalize_current()

        self.current_index = index
        self.current_type = content_type
        self.current_data = {"type": content_type.value, **metadata}

        # Initialize accumulator based on type
        if content_type in (StreamContentType.TEXT, StreamContentType.REASONING):
            self.current_data["text"] = ""

    def add_delta(self, index: int, delta: str | dict[str, Any]) -> None:
        """Add incremental update to current content part."""
        if index != self.current_index:
            raise ValueError(
                f"Delta index {index} doesn't match current {self.current_index}"
            )

        if self.current_type in (StreamContentType.TEXT, StreamContentType.REASONING):
            # Append text delta
            self.current_data["text"] += delta

        elif self.current_type == StreamContentType.TOOL_CALL:
            # Support batch mode only for now
            if isinstance(delta, str):
                self.current_data["input"] = {}
            else:
                self.current_data["input"] = delta

        elif self.current_type == StreamContentType.TOOL_RESULT:
            # Support batch mode only for now
            if isinstance(delta, str):
                self.current_data["output"] = {"type": "text", "value": delta}
            else:
                self.current_data["output"] = {"type": "json", "value": delta}

    def end_content(self, index: int) -> None:
        """Finalize current content part."""
        if index != self.current_index:
            raise ValueError(
                f"End index {index} doesn't match current {self.current_index}"
            )

        # Use provided final content or build from accumulated data
        part = self._build_part_from_data()

        # Store the completed part
        while len(self.parts) <= index:
            self.parts.append(None)
        self.parts[index] = part

        # Reset current tracking
        self.current_index = None
        self.current_type = None
        self.current_data = {}

    def _finalize_current(self) -> None:
        """Internal method to finalize current part."""
        if self.current_index is not None:
            self.end_content(self.current_index)

    def _build_part_from_data(self) -> MessageContentPart:
        """Build a MessageContentPart from current_data."""
        data = self.current_data.copy()

        if self.current_type == StreamContentType.TEXT:
            return MessageTextPart(**data)
        elif self.current_type == StreamContentType.REASONING:
            return MessageReasoningPart(**data)
        elif self.current_type == StreamContentType.TOOL_CALL:
            return MessageToolCallPart(**data)
        elif self.current_type == StreamContentType.TOOL_RESULT:
            return MessageToolResultPart(**data)

        raise ValueError(f"Unknown content type: {self.current_type}")

    def get_all_parts(self) -> list[MessageContentPart]:
        """Get all completed parts."""
        # Finalize any in-progress part
        if self.current_index is not None:
            self._finalize_current()

        # Filter out None values and return
        return [p for p in self.parts if p is not None]
