import argparse
import logging
import os
from collections import defaultdict
from pathlib import Path

from ..data_processing.postprocess import postprocess_irrelevant
from ..utils import get_client, read_config_json, read_prompt, write_config_json

# Setup logging
logger = logging.getLogger(__name__)

QA_KEY = "Irrelevant Unsolvable Question"

REQUIRED_PROMPTS = {QA_KEY}

MAX_PASSES = 3  # hard stop
MAX_PER_DOC = 3  # diversity control


def process_qra_document(model_name: str, file_path: str, prompt_map: dict) -> list:
    """Process each NLP research paper to generate irrelevant questions."""
    client = get_client(model_name)

    config = read_config_json(file_path)

    doc = config["Generated Article"]
    title = config["paperMetadata"]["title"]

    # Prepare tasks
    task = {
        "system_prompt": prompt_map[QA_KEY]["system_prompt"],
        "user_prompt": prompt_map[QA_KEY]["user_prompt"].format(title=title, doc=doc),
    }

    # Generate responses
    response = client.generate([task])[0]

    return postprocess_irrelevant(
        response=response,
        system_prompt=task["system_prompt"],
        user_prompt=task["user_prompt"],
        model_name=model_name,
        name=title,
    )


def generate_qra(
    model_name: str,
    prompt_file: str,
    input_dir: str,
    output_dir: str,
    json_idx: int,
    number: int,
) -> None:
    """Generate Irrelevant Unanswerable Question QRA triples for NLP research papers."""
    prompts = read_prompt(file_path=prompt_file)
    prompt_map = {p["prompt_type"]: p for p in prompts}

    missing = REQUIRED_PROMPTS - prompt_map.keys()
    if missing:
        raise ValueError(f"Missing required prompts: {missing}")

    json_files = [
        f
        for root, dirs, _ in os.walk(input_dir)
        if str(json_idx) in dirs
        for f in Path(root).joinpath(str(json_idx)).glob("*.json")
    ]

    output: list[dict] = []
    per_doc_count = defaultdict(int)
    passes = 0

    while len(output) < number and passes < MAX_PASSES:
        passes += 1
        logger.info(f"Generation pass {passes}")

        for file_path in json_files:
            if per_doc_count[file_path] >= MAX_PER_DOC:
                continue

            try:
                results = process_qra_document(
                    model_name=model_name,
                    file_path=file_path,
                    prompt_map=prompt_map,
                )
            except Exception:
                logging.exception(f"Failed processing file: {file_path}")
                continue

            for r in results:
                output.append(r)
                per_doc_count[file_path] += 1

                if per_doc_count[file_path] >= MAX_PER_DOC:
                    break

            if len(output) >= number:
                break

    if len(output) < number:
        logger.warning(
            f"Only generated {len(output)} / {number} after {passes} passes."
        )

    output_path = Path(output_dir) / "qra_irrelevant.json"
    write_config_json(output_path, output[:number])

    logger.info(
        f"Generated {len(output[:number])} irrelevant QRA triples in '{output_path}'."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate Irrelevant Unanswerable Question QRA triples for NLP research papers."
    )
    parser.add_argument(
        "--model-name",
        type=str,
        required=True,
        help="The model name to use for generating QRA triples.",
    )
    parser.add_argument(
        "--prompt-file", type=str, required=True, help="Path to the prompt JSONL file"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="The input directory containing the JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="The output directory to save the generated QRA triples.",
    )
    parser.add_argument(
        "--json-idx",
        type=int,
        required=True,
        help="The index of the JSON file to process.",
    )
    parser.add_argument(
        "--number",
        type=int,
        required=True,
        help="The number of QRA triples to generate.",
    )

    args = parser.parse_args()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    generate_qra(
        model_name=args.model_name,
        prompt_file=args.prompt_file,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        json_idx=args.json_idx,
        number=args.number,
    )


if __name__ == "__main__":
    main()
