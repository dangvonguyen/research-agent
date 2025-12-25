import argparse
import json
import pathlib
import random
import time

from dotenv import load_dotenv
from openai import OpenAI

from ..utils import load_json_data, save_output

load_dotenv()


def generate_article(
    model_name,
    data_for_complete,
    paper_type,
    paper_details,
):
    time.sleep(random.random() * 1.5)
    system_prompt = "You are an expert NLP researcher writing for top-tier venues (ACL, EMNLP, NeurIPS). Produce publication-quality academic papers with technical depth, clear argumentation, and strong empirical validation."
    user_prompt = f"""Write a complete, publication-ready research paper based on the provided configuration.

RESEARCH CONTEXT:
Topic: {paper_type}
Background: {paper_details}

PAPER STRUCTURE (~5000 words):

1. Abstract (~250 words): Define the problem, full proposed approach, key specific results with numbers, and primary contributions.
2. Introduction (~800 words): Extensive motivation, detailed gap analysis of at least 3 prior works, research questions, contributions list, roadmap.
3. Related Work (~800 words): Comprehensive survey categorized by themes, in-depth comparative analysis, clear positioning.
4. Methodology (~1500 words): Rigorous problem formulation (math), full system architecture details (diagrams in text), training strategy, innovations.
5. Experiments (~1500 words): Detailed setup (datasets, baselines), extensive metric definitions, main results, ablation studies, deep analysis.
6. Results & Analysis (~600 words): Synthesis across settings, interpretation of why it works, failure cases, error analysis.
7. Conclusion (~300 words): Summary of findings, broader impact, future research directions.

WRITING STANDARDS:
- High Information Density: Content must be densely packed with information. Avoid filler language, broad claims, or meta commentary. Replace general statements with specific mechanisms, parameters, or empirical observations.
- Mechanistic Explanation: Do not merely state what the method or contribution does. Explicitly explain why it works, including the underlying inductive biases, optimization effects, or representational advantages that lead to observed improvements.
- Technical Precision: Use standard terminology correctly. Define all symbols and acronyms upon first use.
- Evidence-Based Claims: Avoid subjective adjectives ("amazing", "huge"). Use quantitative descriptors ("15% reduction in latency", "O(n) complexity").
- Cohesive Structure: Ensure smooth transitions between sections. The Methodology must map clearly to the Experiments.
- Scholarly Tone: Maintain a formal, objective tone typical of top-tier NLP venues (ACL/NeurIPS).

MATCHING & FORMATTING:
- Use section headers as shown
- Reference tables/figures in text
- No LaTeX equations; use clear prose
- Prefer paragraphs over bullets

CRITICAL LENGTH INSTRUCTION:
- PROHIBITED: Summarizing, being concise, skipping details, "briefly", "in short".
- REQUIRED: Expand every point. Providing mathematical formulations, detailed logic flows, and hypothetical examples. The goal is to produce a LONG, detailed technical document.
- If the configuration is brief, you must logically extrapolate and fill in the missing technical details to meet the length requirements.

Extract ALL technical details from the configuration JSON below:
"""
    user_prompt += json.dumps(data_for_complete, ensure_ascii=False, indent=2)

    client = OpenAI()

    response = (
        client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
        )
        .choices[0]
        .message.content
    )

    response += f"""\n\nResearch Area Details:\n{paper_details}"""
    return response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="gpt-4o")
    parser.add_argument("--config_dir", type=str, default=None)
    parser.add_argument("--paper_types", type=str, default=None)
    parser.add_argument("--paper_type_idx", type=int, default=None)
    parser.add_argument("--output_dir", type=str, default=None)
    parser.add_argument("--json_idx", type=int, default=0)
    args = parser.parse_args()

    json_idx = args.json_idx
    model_name = args.model_name

    paper_types_list = load_json_data(args.paper_types)
    paper_type_dict = paper_types_list[args.paper_type_idx]
    paper_type, paper_details = paper_type_dict["name"], paper_type_dict["details"]

    data = load_json_data(
        pathlib.Path(args.config_dir)
        / paper_type
        / str(json_idx)
        / f"{json_idx!s}.json"
    )

    response = generate_article(model_name, data, paper_type, paper_details)
    save_output(args.output_dir, response, paper_type, json_idx, None, "txt")


if __name__ == "__main__":
    main()
