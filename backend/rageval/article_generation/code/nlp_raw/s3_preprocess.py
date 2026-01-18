"""Preprocess papers: remove references section and process footnote superscripts.

Usage:
    python -m rageval.article_generation.code.nlp_raw.s3_preprocess \
        --input_dir ./rageval/article_generation/output/nlp_raw/doc/0 \
        --output_dir ./rageval/article_generation/output/nlp_raw/doc_processed
"""

import argparse
import re
import sys
from pathlib import Path

from app.tools.parsers.markdown_parser import MarkdownParser

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))




def remove_references_section(content: str) -> str:
    """
    Remove the references section from markdown content.

    The references section typically starts with a heading like:
    - # References
    - ## References
    - ### References
    - # Bibliography
    - etc.

    Removes everything from the references heading until the next section heading (#)
    or until the end of the document.

    Args:
        content: Markdown content of the paper

    Returns:
        Content with references section removed
    """
    lines = content.split("\n")
    result_lines = []
    in_references = False

    for i, line in enumerate(lines):
        # Check if this line is a heading (starts with #)
        stripped = line.lstrip()
        if stripped.startswith("#"):
            # Check if this heading contains "references" (case-insensitive)
            # Remove the # symbols and check the text
            heading_text = re.sub(r"^#+\s*", "", stripped).lower().strip()
            if "reference" in heading_text or "bibliography" in heading_text:
                # Start of references section - skip this line and everything after
                in_references = True
                continue

            # If we encounter another heading while in references section,
            # it means we've reached the next section (or end of references)
            if in_references:
                # We've reached the next section, stop skipping
                in_references = False
                # Include this new section heading
                result_lines.append(line)
                continue

        # If we're in references section, skip this line
        if in_references:
            continue

        # Otherwise, include this line
        result_lines.append(line)

    return "\n".join(result_lines)


def preprocess_paper(content: str) -> str:
    """
    Preprocess a single paper with all preprocessing steps.

    Args:
        content: Raw markdown content of the paper

    Returns:
        Preprocessed content
    """
    # Step 1: Remove references section
    content = remove_references_section(content)

    # Step 2: Process footnote superscripts
    content = MarkdownParser.preprocess_footnote_sups(content)

    return content


def process_folder(input_folder: Path, output_folder: Path | None = None) -> None:
    """
    Process all .txt files in a folder.

    Args:
        input_folder: Path to folder containing .txt files
        output_folder: Optional output folder. If None, overwrites input files.
    """
    if not input_folder.exists():
        print(f"Input folder not found: {input_folder}")
        return

    if not input_folder.is_dir():
        print(f"Input path is not a directory: {input_folder}")
        return

    # Find all .txt files
    txt_files = sorted(input_folder.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {input_folder}")
        return

    print(f"Found {len(txt_files)} .txt files in {input_folder}")

    # Setup output folder
    if output_folder:
        output_folder.mkdir(parents=True, exist_ok=True)
        print(f"Output folder: {output_folder}")
    else:
        print("Overwriting input files")

    # Process each file
    success_count = 0
    for i, txt_file in enumerate(txt_files):
        paper_id = txt_file.stem
        print(f"\n[{i + 1}/{len(txt_files)}] {paper_id}")

        try:
            # Read content
            content = txt_file.read_text(encoding="utf-8")
            print(f"  Read {len(content)} characters")

            # Preprocess
            preprocessed_content = preprocess_paper(content)
            print(f"  Preprocessed to {len(preprocessed_content)} characters")

            # Determine output path
            if output_folder:
                output_path = output_folder / txt_file.name
            else:
                output_path = txt_file

            # Write output
            output_path.write_text(preprocessed_content, encoding="utf-8")
            print(f"  Saved to: {output_path}")
            success_count += 1

        except Exception as e:
            print(f"  Error processing {paper_id}: {e}")

    print(f"\nCompleted: {success_count}/{len(txt_files)} papers preprocessed")
    if output_folder:
        print(f"Output directory: {output_folder}")


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess papers: remove references and process footnote superscripts"
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        required=True,
        help="Input directory containing .txt paper files",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Output directory for preprocessed papers (if not specified, overwrites input)",
    )
    args = parser.parse_args()

    input_folder = Path(args.input_dir)
    output_folder = Path(args.output_dir) if args.output_dir else None

    process_folder(input_folder, output_folder)


if __name__ == "__main__":
    main()
