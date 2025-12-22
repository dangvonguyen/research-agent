#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/config.sh"

# Corporation settings
DOMAINS=("nlp")
LANGUAGES=("en")
CORPORATION_TYPE='qra'  # 'qra' or 'doc'

run_command() {
    local domains_str=$1

    PYTHONPATH="$SCRIPT_DIR/.." python -m code.data_processing.${CORPORATION_TYPE}_corporation \
        --domains "$domains_str" \
        --output_dir "$RESULTS_DIR"
}

# Convert arrays to comma-separated strings
DOMAINS_STR=$(IFS=,; echo "${DOMAINS[*]}")

# Main execution
run_command "$DOMAINS_STR"
