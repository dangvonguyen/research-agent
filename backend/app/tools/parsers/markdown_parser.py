"""Module for parsing markdown content into sections."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class MarkdownParser:
    """Handles parsing markdown content into sections while preserving structure."""

    def __init__(self, min_content_length: int):
        """
        Initialize markdown parser.

        Args:
            min_content_length: Minimum content length for a section
        """
        self.min_content_length = min_content_length

    @staticmethod
    def extract_section_number(
        section_title: str,
    ) -> Optional[tuple[int, tuple[int, ...], str]]:
        """
        Extract section number from title (e.g., "5.", "5.1", "5.2.3").

        Returns:
            Tuple (level, numbers, title_text) or None if not a numbered section
        """
        pattern = r"^(\d+(?:\.\d+)*)\.?\s*(.*)$"
        match = re.match(pattern, section_title.strip())
        if match:
            numbers = tuple(map(int, match.group(1).split(".")))
            return len(numbers), numbers, match.group(2).strip()
        return None

    @staticmethod
    def is_parent_child(
        parent_num: tuple[int, ...], child_num: tuple[int, ...]
    ) -> bool:
        """Check if child_num is a direct child of parent_num."""
        if len(child_num) != len(parent_num) + 1:
            return False
        return child_num[:-1] == parent_num

    @staticmethod
    def preprocess_footnote_sups(markdown_content: str) -> str:
        """
        Preprocess markdown to move footnote superscripts that appear at the start
        of a line to right after their reference.

        Detects <sup>X</sup> tags that:
        - Start at the beginning of a line (after line break)
        - Are NOT followed by a period
        - Have a matching <sup>X</sup> earlier in the text

        Moves the entire paragraph containing the second sup to right before the first sup.

        Args:
            markdown_content: The markdown content to preprocess

        Returns:
            Preprocessed markdown content
        """
        lines = markdown_content.split("\n")
        # Track which lines to skip (footnote paragraphs that will be moved)
        skip_lines = set()
        # Track insertions: (line_index, position_in_line, text_to_insert)
        insertions = []

        # First pass: identify footnote paragraphs and their target positions
        i = 0
        while i < len(lines):
            line = lines[i]

            # Check if line starts with <sup>X</sup> (after any leading whitespace)
            stripped = line.lstrip()
            sup_match = re.match(r"^<sup>(\d+)</sup>", stripped)

            if sup_match:
                sup_num = sup_match.group(1)
                # Check if NOT followed by a period (after the sup tag)
                after_sup = stripped[len(f"<sup>{sup_num}</sup>") :].lstrip()

                if not after_sup.startswith("."):
                    # This is a candidate - find the paragraph containing this sup
                    paragraph_start = i
                    paragraph_end = i + 1

                    # Collect the entire paragraph (until next blank line or end)
                    while paragraph_end < len(lines) and lines[paragraph_end].strip():
                        paragraph_end += 1

                    paragraph_lines = lines[paragraph_start:paragraph_end]
                    paragraph_text = "\n".join(paragraph_lines)

                    # Find matching sup earlier in the text (before this position)
                    # Search backwards from current position
                    found_match = False
                    for j in range(i - 1, -1, -1):
                        if f"<sup>{sup_num}</sup>" in lines[j]:
                            # Find the position right after the last occurrence of this sup
                            match_pos = lines[j].rfind(f"<sup>{sup_num}</sup>")
                            if match_pos != -1:
                                # Record insertion: add paragraph right after the matching sup
                                after_sup_pos = match_pos + len(f"<sup>{sup_num}</sup>")
                                insertions.append(
                                    (j, after_sup_pos, " " + paragraph_text)
                                )
                                found_match = True
                                break

                    if found_match:
                        # Mark these lines to skip
                        for k in range(paragraph_start, paragraph_end):
                            skip_lines.add(k)
                        i = paragraph_end
                        continue

            i += 1

        # Second pass: build result with insertions and skipping moved paragraphs
        result_lines = []
        for i, line in enumerate(lines):
            if i in skip_lines:
                continue

            # Apply any insertions for this line
            line_insertions = [(pos, text) for idx, pos, text in insertions if idx == i]
            if line_insertions:
                # Sort by position (descending) to insert from end to start
                line_insertions.sort(reverse=True)
                for pos, text in line_insertions:
                    line = line[:pos] + text + line[pos:]

            result_lines.append(line)

        return "\n".join(result_lines)

    @staticmethod
    def extract_markdown_from_inline(inline_token) -> str:
        """
        Extract markdown syntax from an inline token, preserving images, links, and formatting.

        Args:
            inline_token: Inline token from MarkdownIt

        Returns:
            Markdown string preserving all inline elements
        """
        if not inline_token.children:
            return inline_token.content if hasattr(inline_token, "content") else ""

        parts = []
        for child in inline_token.children:
            if child.type == "text":
                parts.append(child.content if hasattr(child, "content") else "")
            elif child.type == "code_inline":
                content = child.content if hasattr(child, "content") else ""
                parts.append(f"`{content}`")
            elif child.type == "image":
                # Extract image markdown: ![alt](src)
                attrs = child.attrs if hasattr(child, "attrs") else []
                alt = ""
                src = ""
                for attr_name, attr_value in attrs:
                    if attr_name == "alt":
                        alt = attr_value
                    elif attr_name == "src":
                        src = attr_value
                parts.append(f"![{alt}]({src})")
            elif child.type == "link_open":
                # Extract link markdown: [text](href)
                attrs = child.attrs if hasattr(child, "attrs") else []
                href = ""
                for attr_name, attr_value in attrs:
                    if attr_name == "href":
                        href = attr_value
                        break
                # Find the link text in following tokens until link_close
                link_text = ""
                link_text_tokens = []
                idx = inline_token.children.index(child) + 1
                while idx < len(inline_token.children):
                    sibling = inline_token.children[idx]
                    if sibling.type == "link_close":
                        break
                    if sibling.type == "text":
                        link_text_tokens.append(
                            sibling.content if hasattr(sibling, "content") else ""
                        )
                    elif sibling.type == "code_inline":
                        # Preserve formatting inside links
                        link_text_tokens.append(
                            f"`{sibling.content if hasattr(sibling, 'content') else ''}`"
                        )
                    idx += 1
                link_text = "".join(link_text_tokens)
                parts.append(f"[{link_text}]({href})")
            elif child.type == "strong_open":
                # Extract bold text
                strong_parts = []
                idx = inline_token.children.index(child) + 1
                while idx < len(inline_token.children):
                    sibling = inline_token.children[idx]
                    if sibling.type == "strong_close":
                        break
                    if sibling.type == "text":
                        strong_parts.append(
                            sibling.content if hasattr(sibling, "content") else ""
                        )
                    idx += 1
                parts.append(f"**{''.join(strong_parts)}**")
            elif child.type == "em_open":
                # Extract italic text
                em_parts = []
                idx = inline_token.children.index(child) + 1
                while idx < len(inline_token.children):
                    sibling = inline_token.children[idx]
                    if sibling.type == "em_close":
                        break
                    if sibling.type == "text":
                        em_parts.append(
                            sibling.content if hasattr(sibling, "content") else ""
                        )
                    idx += 1
                parts.append(f"*{''.join(em_parts)}*")
            elif child.type in ["softbreak", "hardbreak"]:
                parts.append("\n")
            elif child.type in [
                "link_close",
                "strong_close",
                "em_close",
                "image_close",
            ]:
                # Skip close tokens, already handled
                pass

        return "".join(parts)

    @staticmethod
    def extract_content_from_token(tokens: list, start_idx: int) -> str:
        """Extract content from a token and its children."""
        if start_idx >= len(tokens):
            return ""

        token = tokens[start_idx]
        content_parts = []

        if token.type == "paragraph_open":
            idx = start_idx + 1
            while idx < len(tokens) and tokens[idx].type != "paragraph_close":
                if tokens[idx].type == "inline":
                    content_parts.append(
                        MarkdownParser.extract_markdown_from_inline(tokens[idx])
                    )
                idx += 1
        elif token.type in ["bullet_list_open", "ordered_list_open"]:
            idx = start_idx + 1
            depth = 1
            while idx < len(tokens) and depth > 0:
                if tokens[idx].type in ["bullet_list_open", "ordered_list_open"]:
                    depth += 1
                elif tokens[idx].type in ["bullet_list_close", "ordered_list_close"]:
                    depth -= 1
                elif tokens[idx].type == "list_item_open":
                    item_idx = idx + 1
                    item_parts = []
                    while (
                        item_idx < len(tokens)
                        and tokens[item_idx].type != "list_item_close"
                    ):
                        if tokens[item_idx].type == "inline":
                            item_parts.append(
                                MarkdownParser.extract_markdown_from_inline(
                                    tokens[item_idx]
                                )
                            )
                        item_idx += 1
                    if item_parts:
                        content_parts.append("• " + " ".join(item_parts))
                idx += 1

        return " ".join(content_parts).strip()

    def parse_markdown_sections(self, markdown_text: str) -> dict[str, str]:
        """
        Parse markdown text into sections and their content, preserving all markdown syntax.
        Uses raw markdown extraction to preserve images, tables, code blocks, etc.
        Merges short parent sections with their first child section.

        Args:
            markdown_text: The markdown content to parse

        Returns:
            Dictionary with section titles as keys and content as values (preserving markdown)
        """
        # Find all headings in the raw markdown text using regex
        # Pattern matches markdown headings: # Heading, ## Heading, etc.
        heading_pattern = r"^(#{1,6})\s+(.+)$"
        lines = markdown_text.split("\n")

        heading_positions = []  # List of (line_number, heading_level, heading_text)
        for line_num, line in enumerate(lines):
            match = re.match(heading_pattern, line)
            if match:
                heading_level = len(match.group(1))  # Number of # characters
                heading_text = match.group(2).strip()
                heading_positions.append((line_num, heading_level, heading_text))

        if not heading_positions:
            # No headings found, treat entire document as one section
            return {"": markdown_text.strip()}

        # Extract section content as raw markdown between headings
        sections_data = []
        for idx, (line_num, heading_level, heading_text) in enumerate(
            heading_positions
        ):
            # Determine section boundaries
            start_line = line_num + 1  # Content starts after heading line
            if idx + 1 < len(heading_positions):
                end_line = heading_positions[idx + 1][0]  # Until next heading
            else:
                end_line = len(lines)  # Until end of document

            # Extract raw markdown content
            section_lines = lines[start_line:end_line]
            section_content = "\n".join(section_lines).strip()

            # Extract section number if present
            section_info = self.extract_section_number(heading_text)
            if section_info:
                current_level, current_numbers, title_text = section_info
                if title_text:
                    heading_text = (
                        f"{'.'.join(map(str, current_numbers))}. {title_text}"
                    )
            else:
                current_level = heading_level
                current_numbers = None

            sections_data.append(
                {
                    "title": heading_text,
                    "content": section_content,
                    "level": current_level,
                    "numbers": current_numbers,
                }
            )

        # Second pass: merge short parent sections with first child
        sections = {}
        i = 0
        while i < len(sections_data):
            section = sections_data[i]

            if section["numbers"] and len(section["numbers"]) > 0:
                if len(section["content"]) < self.min_content_length:
                    parent_num = section["numbers"]
                    merged_content = section["content"]
                    merged_title = section["title"]

                    j = i + 1
                    while j < len(sections_data):
                        next_section = sections_data[j]
                        if next_section["numbers"] and self.is_parent_child(
                            parent_num, next_section["numbers"]
                        ):
                            merged_title = (
                                f"{section['title']} - {next_section['title']}"
                            )
                            merged_content = f"{section['content']}\n\n{next_section['content']}".strip()
                            sections[merged_title] = merged_content
                            i = j + 1
                            break
                        if (
                            next_section["numbers"]
                            and next_section["numbers"][: len(parent_num)] == parent_num
                        ) or (
                            next_section["numbers"]
                            and len(next_section["numbers"]) <= len(parent_num)
                        ):
                            break
                        j += 1
                    else:
                        sections[section["title"]] = section["content"]
                        i += 1
                        continue
                else:
                    sections[section["title"]] = section["content"]
                    i += 1
            else:
                sections[section["title"]] = section["content"]
                i += 1

        return sections
