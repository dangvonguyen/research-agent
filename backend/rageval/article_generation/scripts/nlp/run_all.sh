#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash ${SCRIPT_DIR}/run_s1.sh
bash ${SCRIPT_DIR}/run_s2.sh
