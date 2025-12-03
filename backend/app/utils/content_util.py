"""Utility functions for working with message content parts."""

from app.types import (
    MessageContentPart,
    MessageTextPart,
    MessageToolCallPart,
    MessageToolResultPart,
)


def extract_text_from_content(content: list[MessageContentPart]) -> str:
    """Extract all text content from a list of content parts.

    Args:
        content: List of content parts

    Returns:
        Concatenated text from all text parts
    """
    text_parts = [part.text for part in content if isinstance(part, MessageTextPart)]
    return "\n\n".join(text_parts)


def create_text_content(text: str) -> list[MessageContentPart]:
    """Create a simple text content part list.

    Args:
        text: Text content

    Returns:
        List containing a single MessageTextPart
    """
    return [MessageTextPart(text=text)]


def has_tool_calls(content: list[MessageContentPart]) -> bool:
    """Check if content contains any tool calls.

    Args:
        content: List of content parts

    Returns:
        True if any content part is a tool call
    """
    return any(isinstance(part, MessageToolCallPart) for part in content)


def get_tool_calls(content: list[MessageContentPart]) -> list:
    """Extract all tool calls from content.

    Args:
        content: List of content parts

    Returns:
        List of MessageToolCallPart items
    """
    return [part for part in content if isinstance(part, MessageToolCallPart)]


def get_tool_results(content: list[MessageContentPart]) -> list:
    """Extract all tool results from content.

    Args:
        content: List of content parts

    Returns:
        List of MessageToolResultPart items
    """
    return [part for part in content if isinstance(part, MessageToolResultPart)]
