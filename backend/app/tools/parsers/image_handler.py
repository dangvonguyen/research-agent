"""Module for handling image extraction, saving, and association with chunks."""

import base64
import logging
import re
from pathlib import Path
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class ImageHandler:
    """Handles image extraction, saving, and association with content chunks."""

    @staticmethod
    def save_images(images: dict, paper_id: UUID, output_dir: Path) -> dict[str, str]:
        """
        Save images from base64-encoded data to filesystem.

        Args:
            images: Dict mapping image names to base64-encoded image data
            paper_id: UUID of the paper
            output_dir: Base directory where paper images are stored

        Returns:
            Dict mapping image names to saved file paths (relative to output_dir)
        """
        if not images:
            return {}

        # Create images directory for this paper
        images_dir = output_dir / str(paper_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        saved_paths = {}
        for image_name, image_data in images.items():
            try:
                # Decode base64 image data
                image_bytes = base64.b64decode(image_data)
                image_path = images_dir / image_name

                # Write image to file
                image_path.write_bytes(image_bytes)
                saved_paths[image_name] = str(image_path.relative_to(output_dir))

                logger.debug("Saved image '%s' to '%s'", image_name, image_path)
            except Exception as e:
                logger.warning(
                    "Failed to save image '%s' for paper '%s': %s",
                    image_name,
                    paper_id,
                    str(e),
                )

        return saved_paths

    @staticmethod
    def extract_image_from_chunk(chunk_content: str) -> Optional[str]:
        """
        Extract image reference from a chunk if it contains one.

        Args:
            chunk_content: Markdown content of the chunk

        Returns:
            Image filename if found, None otherwise
        """
        # Pattern to match markdown images: ![](image.jpg) or ![alt](image.jpg)
        pattern = r"!\[([^\]]*)\]\(([^\)]+)\)"
        matches = re.findall(pattern, chunk_content)

        if matches:
            # Get the last image reference (most relevant one)
            # Format: (alt_text, image_path)
            _, image_path = matches[-1]
            # Extract just the filename from the path
            image_name = Path(image_path).name
            return image_name

        return None

    @staticmethod
    def extract_images_from_content(content: str) -> list[tuple[str, int]]:
        """
        Extract all image references from content with their character positions.

        Args:
            content: Markdown content

        Returns:
            List of tuples: (image_filename, character_position)
        """
        images = []
        pattern = r"!\[([^\]]*)\]\(([^\)]+)\)"
        for match in re.finditer(pattern, content):
            _, image_path = match.groups()
            image_name = Path(image_path).name
            images.append((image_name, match.start()))
        return images

    @staticmethod
    def find_nearest_image(
        chunk_start: int, chunk_end: int, images: list[tuple[str, int]]
    ) -> Optional[str]:
        """
        Find the nearest image to a chunk based on character positions.

        Args:
            chunk_start: Character position where chunk starts in original content
            chunk_end: Character position where chunk ends in original content
            images: List of (image_filename, position) tuples

        Returns:
            Image filename if found nearby, None otherwise
        """
        if not images:
            return None

        # Find images before or after the chunk (within reasonable distance)
        # Consider images up to 500 characters before or after the chunk
        search_range = 500
        nearest_image = None
        min_distance = float("inf")

        for image_name, image_pos in images:
            if image_pos < chunk_start:
                # Image is before chunk
                distance = chunk_start - image_pos
                if distance < search_range and distance < min_distance:
                    min_distance = distance
                    nearest_image = image_name
            elif image_pos > chunk_end:
                # Image is after chunk
                distance = image_pos - chunk_end
                if distance < search_range and distance < min_distance:
                    min_distance = distance
                    nearest_image = image_name
            else:
                # Image is within chunk
                nearest_image = image_name
                break

        return nearest_image
