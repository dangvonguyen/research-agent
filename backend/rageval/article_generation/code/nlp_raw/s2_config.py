"""Generate structured configs from parsed papers using Gemini."""

import argparse
import json
import random
import time
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

from ..utils import load_json_data

load_dotenv()


def generate_config(
    model: genai.GenerativeModel,
    paper_content: str,
    template_schema: dict,
) -> dict | None:
    """
    Extract structured information from paper content using Gemini.

    Args:
        model: Gemini GenerativeModel instance
        paper_content: Markdown content of the paper
        template_schema: JSON schema defining the extraction format

    Returns:
        Extracted configuration as dict, or None if failed
    """
    time.sleep(random.random() * 1.5)

    user_prompt = f"""Extract structured information from this research paper according to the JSON schema below.

RULES:
1. Extract only facts explicitly stated in the paper - never infer or hallucinate
2. Use exact names, numbers, and values as written (e.g., "BERT", "85.3%", "7B parameters")
3. For type_specific: populate ONLY the sub-object matching metadata.paper_type
4. Omit fields where information is not available - do not use null or placeholders
5. Every result in main_findings must have a concrete numeric value

OUTPUT: Valid JSON only.

JSON SCHEMA:
{json.dumps(template_schema, ensure_ascii=False, indent=2)}

PAPER:
{paper_content}
"""

    try:
        response = model.generate_content(
            user_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )

        response_text = response.text
        # Parse JSON response
        result = json.loads(response_text)
        return result

    except json.JSONDecodeError as e:
        print(f"  JSON parsing error: {e}")
        # Try to extract JSON from response
        try:
            response_text = response.text
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end > start:
                result = json.loads(response_text[start:end])
                return result
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"  Error generating config: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate structured configs from parsed papers using Gemini"
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="gemini-2.5-flash",
        help="Gemini model name",
    )
    parser.add_argument(
        "--template_file",
        type=str,
        default="rageval/article_generation/input/nlp_raw/template.json",
        help="Path to JSON schema template",
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        default="rageval/article_generation/output/nlp_raw/doc",
        help="Input directory containing parsed papers",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="rageval/article_generation/output/nlp_raw/config",
        help="Output directory for generated configs",
    )
    parser.add_argument(
        "--json_idx",
        type=int,
        default=0,
        help="Index for organizing inputs/outputs",
    )
    parser.add_argument(
        "--start_idx",
        type=int,
        default=0,
        help="Start processing from this file index",
    )
    parser.add_argument(
        "--end_idx",
        type=int,
        default=None,
        help="End processing at this file index (exclusive)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between API calls in seconds",
    )
    args = parser.parse_args()

    # Load template schema
    template_path = Path(args.template_file)
    if not template_path.exists():
        print(f"Template file not found: {template_path}")
        return

    template_schema = load_json_data(template_path)
    print(f"Loaded template schema from {template_path}")

    # Find input files
    input_dir = Path(args.input_dir) / str(args.json_idx)
    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}")
        return

    paper_files = sorted(input_dir.glob("*.txt"))
    print(f"Found {len(paper_files)} paper files in {input_dir}")

    # Filter by index range
    end_idx = args.end_idx if args.end_idx is not None else len(paper_files)
    paper_files = paper_files[args.start_idx : end_idx]
    print(f"Processing files {args.start_idx} to {end_idx - 1}")

    # Setup output directory
    output_dir = Path(args.output_dir) / str(args.json_idx)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize Gemini
    genai.configure()
    model = genai.GenerativeModel(
        model_name=args.model_name,
        system_instruction="Extract structured data from research papers. Be precise and factual.",
    )

    # Process each paper
    success_count = 0
    for i, paper_file in enumerate(paper_files):
        paper_id = paper_file.stem
        print(f"\n[{i + 1}/{len(paper_files)}] {paper_id}")

        # Check if output already exists
        output_path = output_dir / f"{paper_id}.json"
        if output_path.exists():
            print("  Already processed, skipping")
            success_count += 1
            continue

        # Read paper content
        paper_content = paper_file.read_text(encoding="utf-8")
        print(f"  Read {len(paper_content)} characters")

        # Generate config
        result = generate_config(model, paper_content, template_schema)

        if result:
            # Save config
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  Saved to: {output_path}")
            success_count += 1
        else:
            print("  Failed to generate config")

        # Rate limiting
        if i < len(paper_files) - 1:
            time.sleep(args.delay)

    print(f"\nCompleted: {success_count}/{len(paper_files)} configs generated")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
