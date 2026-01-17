import argparse
import logging
import random
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

# Fields to extract from config for paper comparison (new schema)
CONFIG_FIELDS = [
    "metadata",
    "problem",
    "method",
    "type_specific",
    "experiments",
    "results",
    "contributions",
    "comparisons",
    "limitations",
    "future_work",
]


def extract_paper_view(raw: dict) -> dict:
    """
    Extracts only relevant fields to reduce context window usage.
    """
    return {k: raw[k] for k in CONFIG_FIELDS if k in raw}


def validate_raw_config(cfg: dict, path: str):
    if "metadata" not in cfg:
        raise ValueError(f"Missing 'metadata' in {path}")


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
        logger.error(f"Generate returned {len(responses)} items, expected {len(tasks)}")
        return

    for i, config_key in enumerate(config_keys):
        result_dict[config_key] = postprocess(
            client=client,
            response=responses[i],
            system_prompt=tasks[i]["system_prompt"],
            user_prompt=tasks[i]["user_prompt"],
        )


def process_qra_documents(
    client: Any,
    prompt_map: dict,
    path_1: Path,
    path_2: Path,
    output_dir: Path,
) -> None:
    """Processes multi-document QRA for two NLP research papers."""
    try:
        # Load configs
        raw_1 = read_config_json(path_1)
        raw_2 = read_config_json(path_2)

        # Ensure 'document' in the pair in the config
        if "document" not in raw_1 or "document" not in raw_2:
            logger.warning(
                f"Skipping pair due to missing document: {path_1} or {path_2}"
            )
            return

        # Extract relevant sections from paper configs
        cfg_1 = extract_paper_view(raw_1)
        cfg_2 = extract_paper_view(raw_2)

        title_1 = raw_1["metadata"]["title"]
        title_2 = raw_2["metadata"]["title"]

        qa_results = {}

        # 1. QA Generation
        qa_tasks = []
        qa_keys = []
        for prompt_key, config_key in QA_CONFIG_KEYS:
            qa_tasks.append(
                {
                    "system_prompt": prompt_map[prompt_key]["system_prompt"],
                    "user_prompt": prompt_map[prompt_key]["user_prompt"].format(
                        title1=title_1,
                        title2=title_2,
                        config_1=cfg_1,
                        config_2=cfg_2,
                    ),
                }
            )
            qa_keys.append(config_key)

        process_tasks_and_assign(client, qa_tasks, qa_keys, qa_results)

        # 2. Generate References (dependent on successful QAs)
        ref_tasks = []
        ref_keys = []
        for _, config_key in QA_CONFIG_KEYS:
            if config_key not in qa_results or not qa_results[config_key]:
                continue

            ref_tasks.append(
                {
                    "system_prompt": prompt_map[REF_KEY]["system_prompt"],
                    "user_prompt": prompt_map[REF_KEY]["user_prompt"].format(
                        doc_1=raw_1["document"],
                        doc_2=raw_2["document"],
                        title_1=title_1,
                        title_2=title_2,
                        qa_pairs=qa_results[config_key],
                    ),
                }
            )
            ref_keys.append(config_key)

        process_tasks_and_assign(client, ref_tasks, ref_keys, qa_results)

        # Write output
        file_name = f"{path_1.stem}_{path_2.stem}.json"
        out_path = output_dir / file_name
        write_config_json(out_path, qa_results)

    except Exception as e:
        logger.error(f"Error processing pair {path_1.name} & {path_2.name}: {e}")


def generate_qra(
    model_name: str,
    prompt_file: str,
    input_dir: str,
    output_dir: str,
    json_idx: int,
    number: int,
    max_workers: int = 8,
) -> None:
    """Generate QRA triples for random pairs."""
    prompts = read_prompt(prompt_file)
    prompt_map = {p["prompt_type"]: p for p in prompts}

    missing = REQUIRED_PROMPTS - prompt_map.keys()
    if missing:
        raise ValueError(f"Missing required prompts: {missing}")

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Discover available topics from input directory
    cur_path = input_path / str(json_idx)
    topics = list(cur_path.rglob("*.json"))
    n_topics = len(topics)

    if len(topics) < 2:
        raise ValueError(
            f"Need at least 2 topics with valid files. Found {n_topics}: {topics}"
        )

    # 2. Client Init
    client = get_client(model_name)

    # 3. Pair Sampling
    assert 0 <= number <= n_topics * (n_topics - 1) // 2
    all_pairs = [
        (topics[i], topics[j])
        for i in range(0, n_topics)
        for j in range(i + 1, n_topics)
    ]
    pairs_to_process = random.sample(all_pairs, k=number)

    # 4. Concurrent Execution
    workers = min(max_workers, len(pairs_to_process))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for pair in pairs_to_process:
            path_1, path_2 = pair

            futures.append(
                executor.submit(
                    process_qra_documents,
                    client,
                    prompt_map,
                    path_1,
                    path_2,
                    output_path,
                )
            )

        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Processing Pairs"
        ):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Unhandled worker exception: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate multi-document QRA for NLP research papers."
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
