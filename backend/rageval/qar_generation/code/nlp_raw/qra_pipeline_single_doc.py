import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from tqdm import tqdm

from ..data_processing.postprocess import postprocess
from ..utils import get_client, read_config_json, read_prompt, write_config_json

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

QA_CONFIG_KEYS = [
    ("Factual Question", "qa_fact_based"),
    ("Multi-hop Reasoning Question", "qa_multi_hop"),
    ("Summarization Question", "qa_summary"),
]

REF_KEY = "single document reference"

REQUIRED_PROMPTS = {key for key, _ in QA_CONFIG_KEYS}.union({REF_KEY})


def process_tasks_and_assign(
    client: Any,
    tasks: list[dict[str, Any]],
    config_keys: list[str],
    result_dict: dict,
) -> None:
    """
    Helper to generate responses and run postprocessing.
    """
    responses = client.generate(tasks)

    if len(responses) != len(config_keys):
        logger.error(f"Mismatch: {len(tasks)} tasks vs {len(responses)} responses.")
        return

    for i, config_key in enumerate(config_keys):
        result_dict[config_key] = postprocess(
            client=client,
            response=responses[i],
            system_prompt=tasks[i]["system_prompt"],
            user_prompt=tasks[i]["user_prompt"],
        )


def process_qra_document(
    client: Any,
    file_path: Path,
    prompt_map: dict[str, dict],
    input_dir: Path,
    output_dir: Path,
) -> None:
    """Process each document to generate QRA triples."""
    try:
        config = read_config_json(file_path)
        title = config.get("metadata", {}).get("title", "Unknown Title")

        # Adjust structure: .../config/<idx>/file.json -> .../doc/<idx>/file.txt
        doc_path = (
            file_path.parents[2]
            / "doc"
            / file_path.parent.name
            / file_path.with_suffix(".txt").name
        )

        if not doc_path.exists():
            logger.warning(f"Document file not found: {doc_path}")
            return

        with open(doc_path, encoding="utf-8") as f:
            doc_content = f.read()

        config["document"] = doc_content

        # 1. QA Generation
        qa_tasks = []
        qa_keys = []
        for prompt_key, config_key in QA_CONFIG_KEYS:
            qa_tasks.append(
                {
                    "system_prompt": prompt_map[prompt_key]["system_prompt"],
                    "user_prompt": prompt_map[prompt_key]["user_prompt"].format(
                        config=config, title=title
                    ),
                }
            )
            qa_keys.append(config_key)

        process_tasks_and_assign(client, qa_tasks, qa_keys, config)

        # 2. Reference Extraction (Depends on QA results)
        ref_tasks = []
        ref_keys = []
        for _, config_key in QA_CONFIG_KEYS:
            # Skip if QA generation failed for this key
            if config_key not in config or not config[config_key]:
                continue

            ref_tasks.append(
                {
                    "system_prompt": prompt_map[REF_KEY]["system_prompt"],
                    "user_prompt": prompt_map[REF_KEY]["user_prompt"].format(
                        doc=doc_content, qa_pairs=config[config_key], title=title
                    ),
                }
            )
            ref_keys.append(config_key)

        process_tasks_and_assign(client, ref_tasks, ref_keys, config)

        # Write output
        rel_path = file_path.relative_to(input_dir)
        out_path = output_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_config_json(out_path, config)
    except Exception as e:
        logger.error(f"Failed to process {file_path}: ", e)


def generate_qra(
    model_name: str,
    prompt_file: str,
    input_dir: str,
    output_dir: str,
    json_idx: int,
    max_workers: int = 8,
) -> None:
    """Generate QRA triples for each paper."""
    prompts = read_prompt(prompt_file)
    prompt_map = {p["prompt_type"]: p for p in prompts}

    missing = REQUIRED_PROMPTS - prompt_map.keys()
    if missing:
        raise ValueError(f"Missing required prompts: {missing}")

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Initialize client for connection pool
    client = get_client(model_name)

    # Look for input_dir/<json_dir>/*.json
    target_dir = input_path / str(json_idx)
    if not target_dir.exists():
        logger.error(f"Directory not found: {target_dir}")
        return

    json_files = list(target_dir.glob("*.json"))
    total_files = len(json_files)
    logger.info(f"Found {total_files} files to process in {target_dir}")

    # Set worker count for I/O bound tasks
    workers = min(max_workers, total_files) if total_files > 0 else 1

    # Process each file in parallel
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                process_qra_document,
                client,
                file_path,
                prompt_map,
                input_path,
                output_path,
            ): file_path
            for file_path in json_files
        }

        for future in tqdm(as_completed(futures), total=total_files, desc="Processing"):
            file_path = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"Unhandled exception in thread for {file_path}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate QRA for a single NLP research paper document."
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="gemini-2.5-flash",
        help="Model name (e.g., 'gemini-2.5-flash', 'gpt-4o')",
    )
    parser.add_argument(
        "--prompt-file", type=str, required=True, help="Path to the prompt JSONL file"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing input JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to save output JSON files",
    )
    parser.add_argument(
        "--json-idx", type=int, default=0, help="Index of the JSON files to process"
    )

    args = parser.parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    generate_qra(
        model_name=args.model_name,
        prompt_file=args.prompt_file,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        json_idx=args.json_idx,
    )


if __name__ == "__main__":
    main()
