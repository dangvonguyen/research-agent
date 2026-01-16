"""Parse papers from ACL Anthology URLs using Datalab API."""

import argparse
import re
import tempfile
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from app.tools.parsers.api_converter import APIConverter

load_dotenv()


def download_pdf(url: str, output_path: Path) -> bool:
    """
    Download PDF from ACL Anthology URL.
    """
    # Convert ACL Anthology URL to PDF URL
    # e.g., https://aclanthology.org/2020.emnlp-main.550/ -> https://aclanthology.org/2020.emnlp-main.550.pdf
    pdf_url = url.rstrip("/") + ".pdf"

    try:
        response = requests.get(pdf_url, timeout=60)
        response.raise_for_status()

        output_path.write_bytes(response.content)
        return True
    except requests.RequestException as e:
        print(f"Error downloading PDF from {pdf_url}: {e}")
        return False


def extract_paper_id(url: str) -> str:
    """
    Extract paper ID from ACL Anthology URL.
    """
    # Extract the paper ID from URL
    # e.g., https://aclanthology.org/2020.emnlp-main.550/ -> 2020.emnlp-main.550
    match = re.search(r"aclanthology\.org/([^/]+)/?$", url)
    if match:
        return match.group(1)
    return url.rstrip("/").split("/")[-1]


def sanitize_filename(name: str) -> str:
    """Sanitize string for use as filename."""
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def parse_paper_from_url(
    url: str,
    converter: APIConverter,
) -> tuple[str, str] | None:
    """
    Download and parse a paper from ACL Anthology URL.
    """
    paper_id = extract_paper_id(url)
    print(f"Processing paper: {paper_id}")

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = Path(temp_dir) / f"{paper_id}.pdf"

        # Download PDF
        print("  Downloading PDF...")
        if not download_pdf(url, pdf_path):
            print(f"  Failed to download PDF for {paper_id}")
            return None

        # Convert to markdown using Datalab API
        print("  Converting to markdown...")
        try:
            result = converter.convert_pdf_to_markdown(str(pdf_path))
            markdown_content = result.get("markdown", "")

            if not markdown_content:
                print(f"  No markdown content returned for {paper_id}")
                return None

            print(f"  Successfully parsed {len(markdown_content)} characters")
            return paper_id, markdown_content

        except Exception as e:
            print(f"  Error converting PDF: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(
        description="Parse papers from ACL Anthology URLs using Datalab API"
    )
    parser.add_argument(
        "--urls_file",
        type=str,
        default="rageval/article_generation/input/nlp_raw/urls.txt",
        help="Path to file containing URLs (one per line)",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="rageval/article_generation/output/nlp_raw/doc",
        help="Output directory for parsed papers",
    )
    parser.add_argument(
        "--json_idx",
        type=int,
        default=0,
        help="Index for organizing outputs",
    )
    parser.add_argument(
        "--start_idx",
        type=int,
        default=0,
        help="Start processing from this URL index",
    )
    parser.add_argument(
        "--end_idx",
        type=int,
        default=None,
        help="End processing at this URL index (exclusive)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds",
    )
    args = parser.parse_args()

    # Load URLs
    urls_path = Path(args.urls_file)
    if not urls_path.exists():
        print(f"URLs file not found: {urls_path}")
        return

    urls = [line.strip() for line in urls_path.read_text().splitlines() if line.strip()]
    print(f"Loaded {len(urls)} URLs")

    # Filter by index range
    end_idx = args.end_idx or len(urls)
    urls = urls[args.start_idx : end_idx]
    print(f"Processing URLs {args.start_idx} to {end_idx - 1}")

    # Setup output directory
    output_dir = Path(args.output_dir) / str(args.json_idx)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize converter
    converter = APIConverter()

    # Process each URL
    success_count = 0
    for i, url in enumerate(urls):
        print(f"\n[{i + 1}/{len(urls)}] {url}")

        result = parse_paper_from_url(url, converter)

        if result:
            paper_id, markdown_content = result
            # Save with paper_id as filename (sanitized)
            filename = sanitize_filename(paper_id) + ".txt"
            output_path = output_dir / filename
            output_path.write_text(markdown_content, encoding="utf-8")
            print(f"  Saved to: {output_path}")
            success_count += 1
        else:
            print("  Skipped")

        # Rate limiting
        if i < len(urls) - 1:
            time.sleep(args.delay)

    print(f"\nCompleted: {success_count}/{len(urls)} papers parsed successfully")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
