import argparse
import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..data_processing.postprocess import postprocess
from ..utils import get_client, read_config_json, read_prompt, write_config_json

logger = logging.getLogger(__name__)

QA_CONFIG_KEYS = [
    (
        "Multi-document Information Integration Question",
        "qa_multi_document_information_integration",
    ),
    (
        "Multi-document Comparison Question",
        "qa_multi_document_compare",
    ),
]

REF_KEY = "multi document reference"

REQUIRED_PROMPTS = {key for key, _ in QA_CONFIG_KEYS}.union({REF_KEY})

CONFIG_FIELDS = [
    "paperMetadata",
    "abstract",
    "researchContributions",
    "methodology",
    "experiments",
    "relatedWork",
    "futureWork",
]


def extract_paper_view(raw: dict) -> dict:
    return {k: raw[k] for k in CONFIG_FIELDS if k in raw}


def validate_raw_config(cfg: dict, path: str):
    if "Generated Article" not in cfg:
        raise ValueError(f"Missing 'Generated Article' in {path}")


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


def process_qra_documents(
    model_name: str,
    input_dir: str,
    output_dir: str,
    topic_1: str,
    topic_2: str,
    idx_1: int,
    idx_2: int,
    prompt_map: dict,
) -> None:
    """Processes multi-document QRA for two NLP research papers."""
    client = get_client(model_name)

    # Load configurations for both papers
    path_1 = Path(input_dir) / topic_1 / str(idx_1) / f"{idx_1}.json"
    path_2 = Path(input_dir) / topic_2 / str(idx_2) / f"{idx_2}.json"

    if not (path_1.exists() and path_2.exists()):
        logger.warning(f"Missing input: {path_1} or {path_2}")
        return

    raw_1 = read_config_json(path_1)
    raw_2 = read_config_json(path_2)

    validate_raw_config(raw_1, path_1)
    validate_raw_config(raw_2, path_2)

    # Extract relevant sections from paper configs
    cfg_1 = extract_paper_view(raw_1)
    cfg_2 = extract_paper_view(raw_2)

    title_1 = raw_1["paperMetadata"]["title"]
    title_2 = raw_2["paperMetadata"]["title"]

    # Q/A generation
    qa_results = {}

    qa_tasks = [
        {
            "system_prompt": prompt_map[key]["system_prompt"],
            "user_prompt": prompt_map[key]["user_prompt"].format(
                title1=title_1,
                title2=title_2,
                config_1=cfg_1,
                config_2=cfg_2,
            ),
        }
        for key, _ in QA_CONFIG_KEYS
    ]
    responses = client.generate(qa_tasks)
    postprocess_and_assign(responses, qa_tasks, model_name, qa_results)

    # Reference extraction
    ref_tasks = [
        {
            "system_prompt": prompt_map[REF_KEY]["system_prompt"],
            "user_prompt": prompt_map[REF_KEY]["user_prompt"].format(
                doc_1=raw_1["Generated Article"],
                doc_2=raw_2["Generated Article"],
                qa_pairs=qa_results[config_key],
            ),
        }
        for _, config_key in QA_CONFIG_KEYS
    ]
    responses = client.generate(ref_tasks)
    postprocess_and_assign(responses, ref_tasks, model_name, qa_results)

    # Write output
    file_name = f"{topic_1}-{idx_1}_{topic_2}-{idx_2}.json"
    file_path = Path(output_dir) / file_name
    write_config_json(file_path, qa_results)

    logger.info(f"Finished processing {file_path}.")


def generate_qra(
    model_name: str,
    prompt_file: str,
    input_dir: str,
    output_dir: str,
    json_idx: int,
    number: int,
) -> None:
    """Generate QRA triples for random two NLP research papers."""
    prompts = read_prompt(prompt_file)
    prompt_map = {p["prompt_type"]: p for p in prompts}

    missing = REQUIRED_PROMPTS - prompt_map.keys()
    if missing:
        raise ValueError(f"Missing required prompts: {missing}")

    # Dynamically discover available topics from input directory
    topics = [d.name for d in Path(input_dir).iterdir() if d.is_dir()]

    if len(topics) < 2:
        raise ValueError(
            f"Need at least 2 topics for multi-document QRA generation, "
            f"but only found {len(topics)}: {topics}. "
        )

    rng = random.Random(42)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for _ in range(number):
            t1, t2 = rng.sample(topics, 2)
            i1, i2 = rng.randint(0, json_idx), rng.randint(0, json_idx)

            futures.append(
                executor.submit(
                    process_qra_documents,
                    model_name,
                    input_dir,
                    output_dir,
                    t1,
                    t2,
                    i1,
                    i2,
                    prompt_map,
                )
            )

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error processing future: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate multi-document QRA for NLP research papers."
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
        "--number", type=int, default=10, help="Number of paper pairs to generate"
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
        number=args.number,
    )


if __name__ == "__main__":
    main()
