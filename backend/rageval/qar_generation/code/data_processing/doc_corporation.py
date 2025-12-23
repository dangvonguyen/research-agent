import argparse
import json
from pathlib import Path

FILE_NAME = "DRAGONBALL_docs.jsonl"


def doc_corporation(domains: list[str], input_dir: str, output_dir: str) -> None:
    output_list = []
    doc_id = 0

    for domain in domains:
        domain_dir = Path(input_dir) / domain / "config"
        for root, _, files in domain_dir.walk():
            for file in files:
                if not file.endswith(".json"):
                    continue

                file_path = Path(root) / file
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)

                    metadata = data.get("paperMetadata")
                    title = metadata.get("title")
                    content = data.get("Generated Article")

                    jsonl_obj = {
                        "domain": domain,
                        "doc_id": doc_id,
                        "paper_title": title,
                        "content": content,
                        "metadata": metadata,
                    }
                    output_list.append(jsonl_obj)
                    doc_id += 1

    with open(Path(output_dir) / FILE_NAME, "w", encoding="utf-8") as f:
        for item in output_list:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="corporate docs.")
    parser.add_argument(
        "--domains", type=str, required=True, help="Comma-separated list of domains"
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        required=True,
        help="Input directory for domains' output files",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Output directory for the JSONL file",
    )

    args = parser.parse_args()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Split the comma-separated domains into a list
    domains = args.domains.split(",")

    doc_corporation(
        domains=domains,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
