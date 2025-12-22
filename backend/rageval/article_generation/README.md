# Article Generation Pipeline

This pipeline is designed to generate research documents and academic articles based on configurable schemas and templates. The pipeline uses LLMs to create structured content across multiple research domains.

## Overview

This pipeline automates the creation of research articles through a two-stage process:

1. **Configuration Generation**: Creates structured configurations based on paper templates and research topics
2. **Article Generation**: Generates complete research articles using the configurations

## Prerequisites

### 1. Backend Environment

Ensure the Research Agent backend environment is properly set up with all dependencies installed.

### 2. API Configuration

Set your OpenAI API key in `backend/.env`:

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

## Quick Start

Run the article generation from the `backend/` directory:

```bash
bash scripts/run_article_generation.sh nlp
```

This will:
1. Load the paper types from `rageval/article_generation/output/nlp/schema/paper_types.json`
2. Generate configurations for each paper type
3. Create complete research articles based on those configurations
4. Save outputs to `rageval/article_generation/output/nlp/`

## Directory Structure

```
rageval/article_generation/
├── scripts/
│   └── nlp/
│       ├── config.sh          # Configuration parameters
│       ├── run_s1.sh          # Stage 1: Config generation
│       ├── run_s2.sh          # Stage 2: Article generation
│       └── run_all.sh         # Execute both stages
├── output/
│   └── nlp/
│       ├── schema/            # Input: Paper templates and types
│       ├── config/            # Output: Generated configurations
│       └── doc/               # Output: Generated articles
└── code/
    └── nlp/
        ├── s1_config.py       # Stage 1 implementation
        └── s2_article.py      # Stage 2 implementation
```

## Configuration

### Paper Types Configuration

The `paper_types.json` file defines what types of research papers to generate.

**Location:** `rageval/article_generation/output/nlp/schema/paper_types.json`

**Format:**

```json
[
  {
    "name": "Research Topic Name",
    "details": "Detailed description of the research area, focus points, and key aspects to cover"
  }
]
```

**To customize:**

1. **Add new paper types**: Add new objects to the array
2. **Remove paper types**: Delete objects you don't need
3. **Modify descriptions**: Update the `details` field to guide article generation
4. **Configure range**: Update `PAPER_TYPE_START` and `PAPER_TYPE_END` in `config.sh` to match your paper types

### Generation Parameters

Configure generation behavior in `scripts/nlp/config.sh`:

- `JSON_IDX`: Version index for version control. The default value is `0`. To generate a new version, set this parameter to `1`, `2`, etc.
- `PAPER_SCHEMA_DIR`: Path to schema data folder
- `PAPER_CONFIG_DIR`: Path to configuration output folder
- `PAPER_DOCUMENT_DIR`: Path to document output folder
- `PAPER_TYPE_START`: Starting paper type index (0-based). Set this to the first index you want to process.
- `PAPER_TYPE_END`: Ending paper type index. Set this to the last index you want to process.

**Example:**

If you have 10 paper types in `paper_types.json` (indices 0-9), configure:
```bash
PAPER_TYPE_START=0
PAPER_TYPE_END=9
```


## Pipeline Stages

### Stage 1: Configuration Generation

Creates structured configurations from paper templates and types.

**Input:**
- `paper_template.json`: Template structure for articles
- `paper_types.json`: Research topics to generate

**Output:**
- Configuration files in `output/nlp/config/`

**Run manually:**
```bash
bash rageval/article_generation/scripts/nlp/run_s1.sh
```

### Stage 2: Article Generation

Generates complete research articles based on configurations.

**Input:**
- Configuration files from Stage 1
- Paper types definition

**Output:**
- Complete articles in `output/nlp/doc/`

**Run manually:**
```bash
bash rageval/article_generation/scripts/nlp/run_s2.sh
```
