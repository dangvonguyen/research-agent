# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QAR_GENERATION_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Model configuration
MODEL_NAME="gpt-5-nano"

# Domain settings
DOMAIN="nlp"

# Processing settings
JSON_IDX=0
NUMBER=1

# Directory structure
OUTPUT_BASE_DIR=$QAR_GENERATION_DIR/output
PROMPTS_DIR=$QAR_GENERATION_DIR/prompts
RESULTS_DIR=$QAR_GENERATION_DIR/results
DATA_DIR=$QAR_GENERATION_DIR/data

# Domain-specific directories
DOMAIN_OUTPUT_DIR=$OUTPUT_BASE_DIR/${DOMAIN}
DOMAIN_CONFIG_DIR=$DATA_DIR/${DOMAIN}/config

# Prompt files
PROMPT_FILE=$PROMPTS_DIR/${DOMAIN}.jsonl

# Keypoint generation settings
KEYPOINT_INPUT_FILE=$RESULTS_DIR/DRAGONBALL_query.jsonl
KEYPOINT_OUTPUT_FILE=$RESULTS_DIR/DRAGONBALL_queries.jsonl
