# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTICLE_GENERATION_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"

# Processing settings
JSON_IDX=1

# Model settings
MODEL_NAME="gpt-4o"

# Output directories
NLP_OUTPUT_DIR=$ARTICLE_GENERATION_DIR/output/nlp
PAPER_SCHEMA_DIR=$NLP_OUTPUT_DIR/schema
PAPER_CONFIG_DIR=$NLP_OUTPUT_DIR/config
PAPER_DOCUMENT_DIR=$NLP_OUTPUT_DIR/doc

# Schema file names
PAPER_TEMPLATE_FILE="paper_template.json"
PAPER_TYPES_FILE="paper_types.json"

# Paper type range configuration
PAPER_TYPE_START=0
PAPER_TYPE_END=1
