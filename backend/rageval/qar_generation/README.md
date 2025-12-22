# QAR Generation Pipeline

This pipeline generates Question-Answer-Reference (QAR) triples from research documents and configurations. QAR triples are used to create evaluation datasets for RAG (Retrieval-Augmented Generation) systems.

## Overview

The pipeline creates structured QAR triples through three generation modes:

1. **Single Document**: Generate questions from a single research article
2. **Multi Document**: Generate questions requiring information from multiple articles
3. **Irrelevant Questions**: Generate unanswerable questions for robustness testing

## Prerequisites

### 1. Environment Setup

Ensure you have the backend environment configured with Python 3.12+.

### 2. API Configuration

Set your OpenAI API key in `backend/.env`:

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Input Data

Place generated articles and configurations from the article_generation pipeline in the `data/` directory:
- Configurations: `data/nlp/config/`
- Documents: `data/nlp/doc/`

## Quick Start

Run QAR generation from the `qar_generation/` directory:

```bash
# Single document QAR generation
bash scripts/run_qra_single_doc.sh

# Multi-document QAR generation
bash scripts/run_qra_multi_doc.sh

# Irrelevant question generation
bash scripts/run_qra_irrelevant.sh
```

Output files will be saved to `output/nlp/`.

## Directory Structure

```
rageval/qar_generation/
├── scripts/
│   ├── config.sh                # Shared configuration
│   ├── run_qra_single_doc.sh   # Single document mode
│   ├── run_qra_multi_doc.sh    # Multi document mode
│   └── run_qra_irrelevant.sh   # Irrelevant questions
├── code/
│   ├── nlp/                     # NLP pipeline implementations
│   ├── data_processing/         # Postprocessing utilities
│   └── keypoint_generation/     # Keypoint extraction
├── data/
│   └── nlp/                     # Input: configs and documents
├── output/
│   └── nlp/                     # Output: generated QAR triples
├── prompts/                     # LLM prompts
└── results/                     # Final aggregated datasets
```

## Configuration

Edit `scripts/config.sh` to customize generation:

```bash
MODEL_NAME="gpt-4o"         # LLM model to use
DOMAIN="nlp"                # Domain (nlp, finance, law, medical)
JSON_IDX=0                  # Version index
NUMBER=1                    # Number of multi-doc pairs
```

## Pipeline Modes

### Single Document Mode

Generates QAR triples where all information comes from one article.

**Input:** Article configurations and documents in `data/nlp/`

**Output:** QAR triples in `output/nlp/config/`

**Run:**
```bash
bash scripts/run_qra_single_doc.sh
```

### Multi Document Mode

Generates QAR triples requiring synthesis across multiple articles.

**Input:** Multiple article configurations

**Output:** Cross-document QAR triples in `output/nlp/qra_multidoc/`

**Run:**
```bash
bash scripts/run_qra_multi_doc.sh
```

### Irrelevant Questions Mode

Generates unanswerable questions to test model robustness.

**Input:** Article configurations

**Output:** Irrelevant questions in `output/nlp/qra_irrelevant.json`

**Run:**
```bash
bash scripts/run_qra_irrelevant.sh
```

### Aggregate Results

Firstly, copy all documents from `data/nlp/doc` into `output/nlp/doc`

Combine all QAR triples into a single dataset:

```bash
# Adjust CORPORATION_TYPE as needed
bash scripts/run_corporation.sh
```

Output: `results/DRAGONBALL_queries.jsonl`

### Generate Keypoints

Extract key information from generated questions:

```bash
bash scripts/run_keypoint_generation.sh
```
