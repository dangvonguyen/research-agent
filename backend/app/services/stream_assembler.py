"""Assembles streaming deltas into complete content parts."""

import json
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

    def __init__(self):
        self.parts: list[MessageContentPart | None] = []
        self.current_index: int | None = None
        self.current_type: StreamContentType | None = None
        self.current_data: dict[str, Any] = {}

    def start_content(
        self, content_type: StreamContentType, index: int, **metadata
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
        elif content_type == StreamContentType.TOOL_CALL:
            self.current_data["input"] = {}
            self.current_data["input_buffer"] = ""  # For partial JSON
        elif content_type == StreamContentType.TOOL_RESULT:
            self.current_data["output"] = None
            self.current_data["output_buffer"] = ""  # For partial JSON

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
            # Accumulate JSON chunks for tool call input
            if isinstance(delta, str):
                self.current_data["input_buffer"] += delta
                # Try to parse accumulated JSON
                try:
                    self.current_data["input"] = json.loads(
                        self.current_data["input_buffer"]
                    )
                except json.JSONDecodeError:
                    pass  # Wait for more data
            else:
                # Complete dict update
                self.current_data["input"].update(delta)

        elif self.current_type == StreamContentType.TOOL_RESULT:
            # Accumulate tool result output
            if isinstance(delta, str):
                self.current_data["output_buffer"] += delta
                # Try to parse accumulated JSON
                try:
                    parsed = json.loads(self.current_data["output_buffer"])
                    self.current_data["output"] = parsed
                except json.JSONDecodeError:
                    pass  # Wait for more data
            else:
                # Complete dict update
                self.current_data["output"] = delta

    def end_content(self, index: int) -> MessageContentPart:
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

        # Clean up internal fields
        data.pop("input_buffer", None)
        data.pop("output_buffer", None)

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
