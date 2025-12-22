import argparse
import json
import os
from pathlib import Path


def doc_corporation(domains: list, output_dir: str) -> None:
    output_list = []
    doc_id = 0
    for domain in domains:
        domain_dir = f"output/{domain}"
        for root, _, files in os.walk(domain_dir):
            subfield = Path(root).parent.name
            for file in files:
                if file.endswith(".txt"):
                    file_path = Path(root) / file

                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                        jsonl_obj = {
                            "domain": domain.capitalize(),
                            "doc_id": doc_id,
                            "paper_subfield": subfield,
                            "content": content,
                        }
                        output_list.append(jsonl_obj)
                        doc_id += 1
    new_file_name = "DRAGONBALL_docs.jsonl"
    with open(Path(output_dir) / new_file_name, "w", encoding="utf-8") as f:
        for item in output_list:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="corporate docs.")
    parser.add_argument(
        "--domains", type=str, required=True, help="Comma-separated list of domains"
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

    doc_corporation(domains=domains, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
