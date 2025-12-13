"""Module for classifying and identifying section types."""

import re
from typing import Optional


class SectionClassifier:
    """Handles classification of section types (e.g., references)."""

    @staticmethod
    def is_reference_section(section_title: str) -> bool:
        """
        Check if a section is a reference/bibliography section.

        Reference sections typically start with the keyword and stand alone
        (e.g., "References", "6. References", "Bibliography").
        This avoids false positives like "Related References" or "Citations in Literature".

        Args:
            section_title: Title of the section

        Returns:
            True if this is a reference section
        """
        ref_keywords = [
            "reference",
            "references",
            "bibliography",
            "bibliographies",
            "works cited",
            "citations",
        ]
        title_lower = section_title.lower().strip()

        # Remove section numbers if present (e.g., "6. References" -> "references")
        # Pattern: optional numbers/dots at start, then whitespace, then title
        title_without_number = re.sub(
            r"^(\d+(?:\.\d+)*)\.?\s*", "", title_lower
        ).strip()

        # Check if title starts with keyword and stands alone
        for keyword in ref_keywords:
            # Exact match after removing numbers
            if title_without_number == keyword:
                return True

            # Title starts with keyword
            if title_without_number.startswith(keyword):
                # Get what comes after the keyword
                remaining = title_without_number[len(keyword) :].strip()

                # If nothing after, or only punctuation/whitespace, it's a match
                if not remaining:
                    return True

                # Allow trailing punctuation only
                if remaining in [".", ":", ";", "!", "?"]:
                    return True

                # Allow "References and Acknowledgments" type patterns but reject "References to..." or "Related References"
                if remaining.startswith((" and ", " & ", " or ")):
                    return True

        return False

