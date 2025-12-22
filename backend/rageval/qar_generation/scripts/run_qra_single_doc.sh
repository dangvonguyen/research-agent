#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/config.sh"

run_command() {
    local json_idx=$1

    PYTHONPATH="$SCRIPT_DIR/.." python -m code.${DOMAIN}.qra_pipeline_single_doc \
        --model-name "$MODEL_NAME" \
        --prompt-file "$PROMPT_FILE" \
        --input-dir "$DOMAIN_CONFIG_DIR" \
        --output-dir "$DOMAIN_OUTPUT_DIR/config" \
        --json-idx "$json_idx"
}

# Main execution
run_command "$JSON_IDX"
