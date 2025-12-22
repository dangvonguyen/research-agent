import argparse
import json
import os
from pathlib import Path


def read_jsonl_doc(doc_path: str) -> list:
    docs_data = []
    with open(doc_path, encoding="utf-8") as f:
        for line in f:
            doc = json.loads(line)
            docs_data.append(doc)
    return docs_data


def qa_format_single_doc(domain: str, docs: list[dict]) -> list[dict]:
    key_list = ["qa_fact_based", "qa_multi_hop", "qa_summary"]

    input_path = f"output/{domain}/config"

    output = []

    for root, _, files in os.walk(input_path):
        for file in files:
            if file.endswith(".json"):
                file_path = Path(root) / file
                with open(file_path, encoding="utf-8") as f:
                    json_data = json.load(f)

                doc_id = None

                if domain == "nlp":
                    paper_title: str = json_data["paperMetadata"]["subfield"]

                    for doc in docs:
                        if (
                            "paper_subfield" in doc
                            and doc["paper_subfield"] in paper_title
                        ):
                            doc_id = doc["doc_id"]
                            break

                for key in key_list:
                    for qa in json_data[key]:
                        jsonl_obj = {
                            "domain": domain.capitalize(),
                            "query": {
                                "query_id": 0,
                                "query_type": qa["question type"],
                                "content": qa["question"],
                            },
                            "ground_truth": {
                                "doc_ids": [doc_id],
                                "content": qa["answer"],
                                "references": qa["ref"],
                                "keypoints": "",
                            },
                            "prediction": {"content": "", "references": []},
                        }
                        output.append(jsonl_obj)
    return output


def qa_format_multi_doc(domain: str, docs: list[dict]) -> list[dict]:
    key_list = [
        "qa_multi_document_information_integration",
        "qa_multi_document_compare",
    ]

    input_path = f"output/{domain}/qra_multidoc"

    output = []

    for root, _, files in os.walk(input_path):
        for file in files:
            if file.endswith(".json"):
                file_path = Path(root) / file
                with open(file_path, encoding="utf-8") as f:
                    json_data = json.load(f)

                for key in key_list:
                    doc_ids = []
                    for qa in json_data[key]:
                        ref_list = []

                        for ref in qa["ref"]:
                            for doc in docs:
                                if (
                                    domain == "nlp"
                                    and doc["paper_subfield"] in ref["paper_title"]
                                ):
                                    doc_id = doc["doc_id"]
                                    for r in ref["content"]:
                                        ref_list.append(r)
                                    doc_ids.append(doc_id)
                                    break

                        doc_ids = list(set(doc_ids))

                        jsonl_obj = {
                            "domain": domain.capitalize(),
                            "query": {
                                "query_id": 0,
                                "query_type": qa["question type"],
                                "content": qa["question"],
                            },
                            "ground_truth": {
                                "doc_ids": doc_ids,
                                "content": qa["answer"],
                                "references": ref_list,
                                "keypoints": "",
                            },
                            "prediction": {"content": "", "references": []},
                        }

                        output.append(jsonl_obj)
                        doc_ids = []
    return output


def qa_format_irrelevant(domain: str, docs: list[dict]) -> list[dict]:
    irrelevant_json_path = f"output/{domain}/qra_irrelevant.json"
    with open(irrelevant_json_path, encoding="utf-8") as f:
        json_data = json.load(f)

    output = []
    for item in json_data:
        if domain == "nlp":
            for doc in docs:
                if doc["paper_subfield"] in item["paper_title"]:
                    doc_id = doc["doc_id"]
                    break
        jsonl_obj = {
            "domain": domain.capitalize(),
            "query": {
                "query_id": 0,
                "query_type": item["question type"],
                "content": item["question"],
            },
            "ground_truth": {
                "doc_ids": [doc_id],
                "content": item["answer"],
                "references": item["ref"],
                "keypoints": "",
            },
            "prediction": {"content": "", "references": []},
        }
        output.append(jsonl_obj)
    return output


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

    jsonl_docs = read_jsonl_doc(doc_path="results/DRAGONBALL_docs.jsonl")

    query_list = []
    for domain in domains:
        query_list.extend(qa_format_single_doc(domain=domain, docs=jsonl_docs))
        query_list.extend(qa_format_multi_doc(domain=domain, docs=jsonl_docs))
        query_list.extend(qa_format_irrelevant(domain=domain, docs=jsonl_docs))

    for i, item in enumerate(query_list):
        item["query"]["query_id"] = i

    output_path = args.output_dir + "/DRAGONBALL_query.jsonl"
    with open(output_path, "w") as f:
        for item in query_list:
            json_string = json.dumps(item, ensure_ascii=False)
            f.write(json_string + "\n")


if __name__ == "__main__":
    main()
