#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/config.sh"

run_command() {
    local model_name=$1
    local input_file=$2
    local output_file=$3

    PYTHONPATH="$SCRIPT_DIR/.." python -m code.keypoint_generation.keypoint_generation \
        "$model_name" "$input_file" "$output_file"
}

# Main execution
run_command "$MODEL_NAME" "$KEYPOINT_INPUT_FILE" "$KEYPOINT_OUTPUT_FILE"
