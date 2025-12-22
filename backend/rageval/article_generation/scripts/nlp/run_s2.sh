#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/config.sh"

run_command() {
    local paper_type_idx=$1

    PYTHONPATH="$SCRIPT_DIR/../.." python -m code.nlp.s2_article \
        --config_dir ${PAPER_CONFIG_DIR} \
        --paper_types ${PAPER_SCHEMA_DIR}/${PAPER_TYPES_FILE} \
        --paper_type_idx $paper_type_idx \
        --output_dir ${PAPER_DOCUMENT_DIR} \
        --json_idx $JSON_IDX
}

# Loop through paper type indices
for idx in $(seq $PAPER_TYPE_START $PAPER_TYPE_END); do
    run_command $idx &
done

# Wait for all background processes to complete
wait
