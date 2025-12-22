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
    system_prompt = "You are an experienced NLP researcher with expertise in writing academic papers for top-tier conferences and journals."
    user_prompt = f"""You need to write a complete research paper based on the provided JSON configuration.

The paper is about: {paper_type}
Background: {paper_details}

Based on the provided configuration, write a comprehensive research paper with the following structure:

1. **Abstract** (200-250 words)
   - Concise summary of the problem, approach, experiments, and main results
   - Clear statement of contributions

2. **Introduction** (800-1000 words)
   - Motivate the problem and its importance
   - Describe the current state of the field
   - Clearly state the research questions and contributions
   - Outline the paper structure

3. **Related Work** (1000-1200 words)
   - Survey relevant prior work organized by category
   - Compare and contrast with this work
   - Identify gaps that this research addresses
   - Be specific about methodology and results of related papers

4. **Methodology** (1500-2000 words)
   - Describe the approach in detail
   - Explain the model architecture with specific details (layer counts, dimensions, activation functions)
   - Describe the training procedure (optimization, learning rate schedule, batch size, etc.)
   - Explain key innovations and design choices
   - Include algorithmic descriptions where appropriate
   - Use technical terminology appropriately

5. **Experiments** (1500-2000 words)
   - Describe experimental setup in detail
   - List datasets with statistics (size, splits, characteristics)
   - Describe baselines and their configurations
   - Present evaluation metrics and justify their choice
   - Include detailed results tables in text form
   - Provide thorough analysis and ablation studies
   - Discuss what the results show and why

6. **Results and Analysis** (800-1000 words)
   - Highlight main findings
   - Provide in-depth analysis of results
   - Discuss strengths and limitations
   - Include error analysis or case studies if relevant
   - Compare with theoretical expectations

7. **Conclusion** (400-500 words)
   - Summarize the main contributions
   - Discuss broader implications
   - Describe future work and potential extensions
   - End with a strong closing statement

Guidelines:
- Write in a formal academic tone
- Use technical terminology appropriately
- Be specific about numbers, metrics, and technical details
- Make the paper coherent and well-structured
- Total length should be 6000-8000 words
- Do not include actual equations in LaTeX, but describe mathematical concepts in text
- Reference the provided JSON configuration for all technical details

The configuration JSON:
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
