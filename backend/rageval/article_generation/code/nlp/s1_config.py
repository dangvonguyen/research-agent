import argparse
import json
import random
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from ..utils import load_json_data, save_output

load_dotenv()


first_names = [
    'Alex', 'Jordan', 'Sam', 'Taylor', 'Casey', 'Morgan', 'Jamie', 'Riley',
    'Avery', 'Quinn', 'Rowan', 'Sage', 'Blake', 'Dakota', 'Parker', 'Skyler',
    'Cameron', 'Hayden', 'Peyton', 'Drew', 'Reese', 'Finley', 'Emerson', 'Harper',
    'Charlie', 'Phoenix', 'River', 'Kai', 'Micah', 'Adrian', 'Elliot', 'Jesse',
    'Robin', 'Kendall', 'Alexis', 'Dylan', 'Devon', 'Logan', 'Bailey', 'Reagan',
    'Tatum', 'Sidney', 'Sawyer', 'Ashton', 'Emery', 'Rory', 'Sloan', 'Ellis',
    'Ryan', 'Spencer', 'Shawn', 'Angel', 'Marley', 'Justice', 'Milan', 'Ocean'
]  # fmt: skip
last_names = [
    'Zhang', 'Wang', 'Li', 'Chen', 'Liu', 'Yang', 'Huang', 'Zhao', 'Wu', 'Zhou',
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Kumar', 'Patel', 'Singh', 'Sharma', 'Gupta', 'Reddy', 'Rao', 'Iyer',
    'Kim', 'Park', 'Lee', 'Choi', 'Jung', 'Kang', 'Cho', 'Yoon',
    'Tanaka', 'Suzuki', 'Takahashi', 'Watanabe', 'Ito', 'Yamamoto', 'Nakamura',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Perez', 'Sanchez',
    'Müller', 'Schmidt', 'Schneider', 'Fischer', 'Weber', 'Meyer', 'Wagner',
    'Cohen', 'Levy', 'Rosenberg', 'Goldstein', 'Friedman', 'Katz', 'Schwartz',
    'Ali', 'Ahmed', 'Hassan', 'Hussein', 'Mohamed', 'Ibrahim', 'Abdullah',
    'Silva', 'Santos', 'Oliveira', 'Costa', 'Ferreira', 'Rodrigues', 'Alves',
    'Novak', 'Kowalski', 'Nowak', 'Wojcik', 'Lewandowski', 'Zieliński',
    'Ivanov', 'Smirnov', 'Kuznetsov', 'Popov', 'Sokolov', 'Lebedev', 'Kozlov'
]  # fmt: skip
venues = [
    'ACL', 'AACL', 'CL', 'CoNLL', 'EACL', 'EMNLP', 'NAACL', 'NAACL', 'TACL',
    'WMT', 'WS', 'SemEval', 'NeurIPS', 'ICML', 'ICLR', 'AAAI', 'IJCAI',
]  # fmt: skip
years = ["2020", "2021", "2022", "2023", "2024", "2025"]


def generate_config(
    model_name,
    data_for_complete,
    paper_type,
    paper_details,
):
    time.sleep(random.random() * 1.5)
    system_prompt = "You are an experienced NLP researcher with expertise in writing academic papers and designing experiments."
    user_prompt = f"""You need to generate a detailed research paper configuration in JSON format.

The paper is about: {paper_type}
Background: {paper_details}

You need to fill in the following JSON template with realistic and technically sound information:
- The "paperMetadata" section has been pre-filled with title, authors, venue, year, and subfield.
- Fill in "abstract": A concise 200-300 word summary of the paper.
- Fill in "researchContributions": List 2-4 main contributions with detailed descriptions and novelty explanations.
- Fill in "methodology": Describe the approach, model architecture (be specific with layer counts, dimensions, attention mechanisms), training strategy, and 3-5 key innovations.
- Fill in "experiments": Design 2-4 experiments with specific dataset names, baseline methods, evaluation metrics (with expected values), results (be realistic), and analysis.
- Fill in "relatedWork": List 2-3 categories of related work with representative papers and how this work differs.
- Fill in "futureWork": Provide 2-3 promising future directions.

Important:
- Be technically specific (mention specific architectures, hyperparameters, dataset sizes, metric values)
- Make the research contributions novel and believable
- Ensure experiments are well-designed with appropriate baselines and metrics
- Use realistic metric values (e.g., BLEU scores 20-45, F1 scores 0.70-0.95, perplexity 10-100)
- Make sure all lists have actual content, not empty arrays

The JSON template to complete:
"""
    user_prompt += json.dumps(data_for_complete, ensure_ascii=False, indent=2)

    client = OpenAI()

    while True:
        try:
            response = (
                client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                )
                .choices[0]
                .message.content
            )
            response = response[response.find("{") : response.rfind("}") + 1]
            response = json.loads(response)
            break
        except Exception as e:
            print(f"Error occurred: {e}. Retrying...")
            time.sleep(1)
    return response


def set_value(data, paper_type) -> dict[str, Any]:
    # Generate random authors (3-6 authors)
    num_authors = random.randint(3, 6)
    authors = []
    for _ in range(num_authors):
        first = random.choice(first_names)
        last = random.choice(last_names)
        authors.append(f"{first} {last}")

    # Generate a plausible paper title based on paper type
    title_templates = [
        f"Advancing {paper_type}: A Novel Approach",
        f"{paper_type}: Methods and Applications",
        f"Efficient {paper_type} via Neural Architecture",
        f"Scaling {paper_type} with Transformers",
        f"Learning Representations for {paper_type}",
        f"A Comprehensive Study of {paper_type}",
        f"Towards Better {paper_type}: An Empirical Analysis",
        f"Rethinking {paper_type} Design",
    ]

    data["paperMetadata"]["title"] = random.choice(title_templates)
    data["paperMetadata"]["authors"] = authors
    data["paperMetadata"]["venue"] = random.choice(venues)
    data["paperMetadata"]["year"] = random.choice(years)
    data["paperMetadata"]["subfield"] = paper_type

    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="gpt-4o-mini")
    parser.add_argument("--data_for_complete", type=str, default=None)
    parser.add_argument("--paper_types", type=str, default=None)
    parser.add_argument("--paper_type_idx", type=int, default=None)
    parser.add_argument("--output_dir", type=str, default=None)
    parser.add_argument("--json_idx", type=int, default=0)
    args = parser.parse_args()

    json_idx = args.json_idx
    model_name = args.model_name

    data = load_json_data(args.data_for_complete)

    paper_types_list = load_json_data(args.paper_types)
    paper_type_dict = paper_types_list[args.paper_type_idx]
    paper_type, paper_details = paper_type_dict["name"], paper_type_dict["details"]

    data = set_value(data, paper_type)

    response = generate_config(model_name, data, paper_type, paper_details)
    save_output(args.output_dir, response, paper_type, json_idx, None, "json")


if __name__ == "__main__":
    main()
