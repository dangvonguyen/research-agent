#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/config.sh"

run_command() {
    local number=$1
    local json_idx=$2

    PYTHONPATH="$SCRIPT_DIR/.." python -m code.${DOMAIN}.qra_pipeline_irrelevant \
        --model-name "$MODEL_NAME" \
        --prompt-file "$PROMPT_FILE" \
        --input-dir "$DOMAIN_OUTPUT_DIR/config" \
        --output-dir "$DOMAIN_OUTPUT_DIR" \
        --number "$number" \
        --json-idx "$json_idx"
}

# Main execution
run_command "$NUMBER" "$JSON_IDX"
