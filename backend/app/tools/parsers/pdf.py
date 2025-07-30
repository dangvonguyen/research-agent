import logging
import re

from pypdf import PdfReader

from app.models import PaperCreate, PaperSection

logger = logging.getLogger(__name__)


class PDFParser:
    """A parser to extract sections from PDF research papers."""

    def __init__(self) -> None:
        # Common section patterns (case-insensitive)
        self.section_patterns = {
            "abstract": [
                r"\babstract\b",
                r"\bsummary\b",
            ],
            "introduction": [
                r"\bintroduction\b",
                r"\bbackground\b",
                r"\bmotivation\b",
            ],
            "conclusion": [
                r"\bconclusion\b",
                r"\bconclusions\b",
                r"\bfinal\s+thoughts\b",
            ],
        }

        self.heading_patterns = [
            {
                "pattern": r"^((?:[A-Z]|\d+)(?:\.\d+)*)\s+((?:[A-Z]|\d+)[A-Za-z\s\-:]+)$",
                "type": "numbered",
            },
            {
                "pattern": r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})$",
                "type": "titlecase",
            },
        ]

        self.common_title_case_patterns = [
            "abstract",
            "limitations",
            "ethics statement",
            "ethical statement",
            "ethical considerations",
            "acknowledgement",
            "acknowledgements",
            "references",
        ]

    def parse_paper(self, paper: PaperCreate) -> dict[str, PaperSection]:
        """
        Parse a research paper text and extract sections.
        """
        if not paper.local_pdf_path:
            logger.warning("No local PDF path provided for paper %s", paper.source_id)
            return {}

        logger.debug("Parsing PDF paper %s", paper.local_pdf_path)
        try:
            reader = PdfReader(paper.local_pdf_path)
            logger.debug("PDF loaded with %d pages", len(reader.pages))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"

            logger.debug("Extracted %d characters of text", len(text))

            # Normalize text
            text = self._normalize_text(text)

            # Find all potential headings
            headings = self._find_headings(text)

            # Classify headings into section types
            sections = self._classify_sections(headings, text)

            return sections

        except Exception as e:
            logger.error("Error parsing PDF: %s", str(e))
            return {}

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for better parsing.
        """
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()

    def _find_headings(self, text: str) -> list[tuple[str, int, int]]:
        """
        Find potential section headings in the text.

        Returns:
            List of tuples (heading_text, start_pos, heading_level)
        """
        logger.debug("Finding section headings")
        headings = []
        lines = text.splitlines(True)  # Keep line endings
        current_pos = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                current_pos += len(line)
                continue

            # Check each heading pattern
            for pattern_info in self.heading_patterns:
                match = re.match(pattern_info["pattern"], stripped)
                if match:
                    if pattern_info["type"] == "numbered":
                        level = len(match.group(1).strip(".").split("."))
                        heading_text = match.group(2).strip()
                    else:
                        level = 1
                        heading_text = match.group(1).strip()
                        if heading_text.lower() not in self.common_title_case_patterns:
                            continue

                    logger.debug(
                        "Found heading: '%s' (level %d) at position %d",
                        heading_text, level, current_pos,
                    )
                    headings.append((heading_text, current_pos, level))
                    break

            current_pos += len(line)

        logger.debug("Found %d potential section headings", len(headings))
        return headings

    def _classify_sections(
        self, headings: list[tuple[str, int, int]], text: str
    ) -> dict[str, PaperSection]:
        """
        Classify headings into section types and extract content.
        """
        logger.debug("Classifying sections from %d headings", len(headings))
        sections = {}

        for i, (heading_text, start_pos, level) in enumerate(headings):
            # Determine end position (start of next heading or end of text)
            if i + 1 < len(headings):
                end_pos = headings[i + 1][1]
            else:
                end_pos = len(text)

            # Extract content
            content = text[start_pos:end_pos].strip()

            # Remove the heading from content
            lines = content.split("\n")
            if lines:
                content = "\n".join(lines[1:]).strip()

            # Classify section type
            section_type = self._classify_section_type(heading_text)
            logger.debug(
                "Classified heading '%s' as section type '%s'",
                heading_text, section_type,
            )

            section = PaperSection(title=heading_text, content=content, level=level)
            sections[section_type] = section

        return sections

    def _classify_section_type(self, heading_text: str) -> str:
        """
        Classify a heading into a section type.
        """
        heading_lower = heading_text.lower()

        # Check against patterns
        for section_type, patterns in self.section_patterns.items():
            for pattern in patterns:
                if re.search(pattern, heading_lower, re.IGNORECASE):
                    return section_type

        # If no match found, use the original heading as section type
        return re.sub(r"[^\w\s]", "_", heading_lower).lower().replace(" ", "_")

    def parse_specific_sections(
        self, paper: PaperCreate, section_types: list[str]
    ) -> dict[str, PaperSection]:
        """
        Extract only specific section types.
        """
        logger.debug(
            "Parsing specific sections for paper %s: %s",
            paper.source_id, section_types,
        )

        all_sections = self.parse_paper(paper)
        found_sections = {k: v for k, v in all_sections.items() if k in section_types}
        missing_sections = [s for s in section_types if s not in found_sections]

        if missing_sections:
            logger.warning(
                "Could not find sections %s for paper %s",
                missing_sections, paper.source_id,
            )

        return found_sections
