import argparse
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..data_processing.postprocess import postprocess
from ..utils import get_client, read_config_json, read_prompt, write_config_json

logger = logging.getLogger(__name__)

QA_CONFIG_KEYS = [
    ("Factual Question", "qa_fact_based"),
    ("Multi-hop Reasoning Question", "qa_multi_hop"),
    ("Summarization Question", "qa_summary"),
]

REF_KEY = "single document reference"

REQUIRED_PROMPTS = {key for key, _ in QA_CONFIG_KEYS}.union({REF_KEY})


def postprocess_and_assign(
    responses: list[str], tasks: list[dict[str, Any]], model_name: str, result: dict
) -> None:
    for i, (_, config_key) in enumerate(QA_CONFIG_KEYS):
        result[config_key] = postprocess(
            response=responses[i],
            system_prompt=tasks[i]["system_prompt"],
            user_prompt=tasks[i]["user_prompt"],
            model_name=model_name,
        )


def process_qra_document(
    model_name: str,
    file_path: str,
    prompt_map: dict[str, dict],
    input_dir: str,
    output_dir: str,
) -> None:
    """Process each document to generate QRA triples."""
    client = get_client(model_name)
    config = read_config_json(file_path)

    title = config["paperMetadata"]["title"]

    # Load document
    doc_path = file_path.replace("config", "doc").replace(".json", ".txt")
    with open(doc_path, encoding="utf-8") as f:
        doc_content = f.read()

    config["Generated Article"] = doc_content

    # Q/A generation
    qa_tasks = [
        {
            "system_prompt": prompt_map[key]["system_prompt"],
            "user_prompt": prompt_map[key]["user_prompt"].format(
                config=config, title=title
            ),
        }
        for key, _ in QA_CONFIG_KEYS
    ]
    responses = client.generate(qa_tasks)
    postprocess_and_assign(responses, qa_tasks, model_name, config)

    # Reference extraction
    ref_tasks = [
        {
            "system_prompt": prompt_map[REF_KEY]["system_prompt"],
            "user_prompt": prompt_map[REF_KEY]["user_prompt"].format(
                doc=doc_content, qa_pairs=config[config_key]
            ),
        }
        for _, config_key in QA_CONFIG_KEYS
    ]
    responses = client.generate(ref_tasks)
    postprocess_and_assign(responses, ref_tasks, model_name, config)

    # Write output
    rel_path = os.path.relpath(file_path, input_dir)
    out_path = Path(output_dir) / rel_path
    out_path.mkdir(parents=True, exist_ok=True)
    write_config_json(out_path, config)

    logger.info(f"Finished processing: {out_path}.")


def generate_qra(
    model_name: str, prompt_file: str, input_dir: str, output_dir: str, json_idx: int
) -> None:
    """Generate QRA triples for each paper."""
    prompts = read_prompt(prompt_file)
    prompt_map = {p["prompt_type"]: p for p in prompts}

    missing = REQUIRED_PROMPTS - prompt_map.keys()
    if missing:
        raise ValueError(f"Missing required prompts: {missing}")

    # Collect JSON files for processing
    json_files = [
        file
        for root, dirs, files in os.walk(input_dir)
        if str(json_idx) in dirs
        for file in Path(root).joinpath(str(json_idx)).glob("*.json")
    ]

    # Process each file in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(
                process_qra_document,
                model_name,
                file_path,
                prompt_map,
                input_dir,
                output_dir,
            )
            for file_path in json_files
        ]

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error processing file: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate QRA for a single NLP research paper document."
    )
    parser.add_argument(
        "--model-name", type=str, required=True, help="Name of the OpenAI model to use"
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
