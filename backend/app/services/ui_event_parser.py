"""Parser to extract structured JSON UI events from text stream."""

import json
import logging
import re
from typing import Any

from app.types import CustomUIEvent

logger = logging.getLogger(__name__)


def extract_all_json_objects_from_text(
    text: str, expected_types: list[str] | None = None
) -> list[tuple[dict[str, Any], int, int]]:
    """Extract all JSON objects from text that match expected types.

    Returns list of (json_data, start_pos, end_pos) tuples.
    Handles JSON with newlines and whitespace in string values.
    """
    if expected_types is None:
        expected_types = ["citations", "paper_recommendation"]

    results = []

    # Try to find all JSON objects in the text
    # Look for balanced braces, handling strings properly
    i = 0
    while i < len(text):
        if text[i] == "{":
            brace_count = 0
            start_idx = i
            in_string = False
            escape_next = False

            # Find matching closing brace, handling strings
            for j in range(i, len(text)):
                char = text[j]

                if escape_next:
                    escape_next = False
                    continue

                if char == "\\":
                    escape_next = True
                    continue

                if char == '"':
                    in_string = not in_string
                    continue

                if not in_string:
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            # Found complete JSON object
                            json_str = text[start_idx : j + 1]
                            try:
                                # Try parsing as-is first
                                parsed = json.loads(json_str)
                                if (
                                    isinstance(parsed, dict)
                                    and parsed.get("type") in expected_types
                                ):
                                    results.append((parsed, start_idx, j + 1))
                                    logger.debug(
                                        f"Successfully parsed JSON at {start_idx}-{j + 1}: type={parsed.get('type')}"
                                    )
                            except json.JSONDecodeError:
                                # If parsing fails, try cleaning up the JSON
                                try:
                                    # Remove newlines and extra whitespace from string values
                                    cleaned_json = json_str
                                    # Try to clean URL fields that might have newlines
                                    # Handle multi-line strings in JSON
                                    cleaned_json = re.sub(
                                        r'"url"\s*:\s*"([^"]*?)"',
                                        lambda m: f'"url":"{m.group(1).replace(chr(10), "").replace(chr(13), "").replace(" ", "").strip()}"',
                                        cleaned_json,
                                        flags=re.DOTALL,
                                    )
                                    # Clean title fields too
                                    cleaned_json = re.sub(
                                        r'"title"\s*:\s*"([^"]*?)"',
                                        lambda m: f'"title":"{m.group(1).replace(chr(10), " ").replace(chr(13), " ").strip()}"',
                                        cleaned_json,
                                        flags=re.DOTALL,
                                    )
                                    # Normalize whitespace between JSON tokens
                                    cleaned_json = re.sub(r"\s+", " ", cleaned_json)
                                    cleaned_json = re.sub(r",\s*}", "}", cleaned_json)
                                    cleaned_json = re.sub(r",\s*]", "]", cleaned_json)

                                    parsed = json.loads(cleaned_json)
                                    print("parsed", parsed)
                                    if (
                                        isinstance(parsed, dict)
                                        and parsed.get("type") in expected_types
                                    ):
                                        results.append((parsed, start_idx, j + 1))
                                        logger.debug(
                                            f"Successfully parsed cleaned JSON at {start_idx}-{j + 1}: type={parsed.get('type')}"
                                        )
                                except (json.JSONDecodeError, Exception) as e2:
                                    logger.debug(
                                        f"Failed to parse JSON at {start_idx}-{j + 1}: {e2}. JSON preview: {json_str[:200]}"
                                    )
                                    pass
                            i = j + 1
                            break
            else:
                i += 1
        else:
            i += 1

    return results


def extract_json_from_text(
    text: str, expected_types: list[str] | None = None
) -> dict[str, Any] | None:
    """Extract complete JSON object from text.

    Looks for JSON objects wrapped in << ... >> markers or standalone.
    Returns the first valid JSON object found.

    Args:
        text: The text content to parse
        expected_types: List of expected "type" values (e.g., ["citations", "paper_recommendation"])
                       If None, accepts any type

    Returns:
        Parsed JSON dict if found, None otherwise
    """
    if expected_types is None:
        expected_types = ["citations", "paper_recommendation"]

    # Pattern 1: JSON in markers (<< ... >>)
    marker_pattern = r"<<\s*(\{.*?\})\s*>>"
    match = re.search(marker_pattern, text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict) and parsed.get("type") in expected_types:
                return parsed
        except json.JSONDecodeError:
            pass

    # Pattern 2: Standalone JSON object
    # Look for { ... } that starts with "type": expected_type
    for expected_type in expected_types:
        json_pattern = rf'\{{[^{{}}]*"type"\s*:\s*"{expected_type}"[^{{}}]*\{{[^{{}}]*\}}[^{{}}]*\}}'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict) and parsed.get("type") in expected_types:
                    return parsed
            except json.JSONDecodeError:
                pass

    # Pattern 3: Try to find any complete JSON object
    # Look for balanced braces
    brace_count = 0
    start_idx = -1
    for i, char in enumerate(text):
        if char == "{":
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                json_str = text[start_idx : i + 1]
                try:
                    parsed = json.loads(json_str)
                    # Check if it has the expected structure
                    if (
                        isinstance(parsed, dict)
                        and parsed.get("type") in expected_types
                    ):
                        return parsed
                except json.JSONDecodeError:
                    pass
                start_idx = -1

    return None


def parse_ui_events_from_text(text: str) -> list[tuple[CustomUIEvent, int, int]]:
    """Parse all UI event JSONs from text and return UI events with positions.

    Extracts all JSON objects with type "citations" or "paper_recommendation" from text.
    Supports both array format (old) and object format (new inline citations).

    Args:
        text: The text content to parse

    Returns:
        List of tuples: (CustomUIEvent, json_start_pos, json_end_pos)
        Positions are -1 if JSON not found
    """
    events = []
    expected_types = ["citations", "paper_recommendation"]

    # Extract all JSON objects from text
    json_objects = extract_all_json_objects_from_text(text, expected_types)

    for json_data, json_start_pos, json_end_pos in json_objects:
        expected_type = json_data.get("type")

        if expected_type == "citations":
            citations_data = json_data.get("citations")

            # Support both array format (old) and object format (new)
            if isinstance(citations_data, dict):
                # New format: single citation object
                citation = {
                    "url": citations_data.get("url", ""),
                }

                if citations_data.get("title"):
                    citation["title"] = citations_data["title"]

                if citation.get("url"):
                    events.append(
                        (
                            CustomUIEvent(
                                event_type="citations",
                                data={
                                    "title": json_data.get("title", "Sources"),
                                    "citations": citation,  # Single object, not array
                                },
                            ),
                            json_start_pos,
                            json_end_pos,
                        )
                    )
            elif isinstance(citations_data, list):
                # Old format: array of citations
                citations = []
                for citation_data in citations_data:
                    if not isinstance(citation_data, dict):
                        continue

                    citation = {
                        "number": citation_data.get("number"),
                        "url": citation_data.get("url", ""),
                    }

                    if citation_data.get("title"):
                        citation["title"] = citation_data["title"]

                    if citation_data.get("text"):
                        citation["text"] = citation_data["text"]

                    if citation.get("url"):
                        citations.append(citation)

                if citations:
                    events.append(
                        (
                            CustomUIEvent(
                                event_type="citations",
                                data={
                                    "title": json_data.get("title", "Sources"),
                                    "citations": citations,
                                },
                            ),
                            json_start_pos,
                            json_end_pos,
                        )
                    )

        elif expected_type == "paper_recommendation":
            papers_data = json_data.get("papers", [])
            if not papers_data or not isinstance(papers_data, list):
                continue

            papers = []
            for paper_data in papers_data:
                if not isinstance(paper_data, dict):
                    continue

                paper = {
                    "title": paper_data.get("title", ""),
                    "url": paper_data.get("url", ""),
                }

                if paper_data.get("reason"):
                    paper["reason"] = paper_data["reason"]

                if paper_data.get("authors"):
                    paper["authors"] = paper_data["authors"]

                if paper_data.get("year"):
                    paper["year"] = paper_data["year"]

                if paper.get("title") and paper.get("url"):
                    papers.append(paper)

            if papers:
                events.append(
                    (
                        CustomUIEvent(
                            event_type="paper_recommendations",
                            data={
                                "title": json_data.get(
                                    "title", "Recommended Papers for Deep Analysis"
                                ),
                                "message": json_data.get("message"),
                                "papers": papers,
                            },
                        ),
                        json_start_pos,
                        json_end_pos,
                    )
                )

    # Sort by position (earliest first)
    events.sort(key=lambda x: x[1])
    return events


def parse_paper_recommendations_from_text(
    text: str,
) -> tuple[CustomUIEvent | None, str, int, int]:
    """Parse paper recommendations JSON from text and return UI event.

    Extracts JSON from text, removes it from text, and returns UI event with JSON positions.
    This is a legacy function for backward compatibility.

    Args:
        text: The text content to parse

    Returns:
        Tuple of (CustomUIEvent if found, text_with_json_removed, json_start_pos, json_end_pos)
        Positions are -1 if JSON not found
    """
    events = parse_ui_events_from_text(text)

    # Find first paper_recommendation event
    for event, json_start_pos, json_end_pos in events:
        if event.event_type == "paper_recommendations":
            # Remove JSON from text
            text_cleaned = text[:json_start_pos] + text[json_end_pos:]
            # Clean up extra whitespace
            text_cleaned = re.sub(r"\n{3,}", "\n\n", text_cleaned).strip()
            return event, text_cleaned, json_start_pos, json_end_pos

    return None, text, -1, -1
