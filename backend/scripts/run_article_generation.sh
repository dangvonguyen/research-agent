#!/bin/bash

# Set the parameters
domain=$1

# Check if parameters are provided
if [ -z "$domain" ]; then
  echo "Usage: $0 <domain>"
  exit 1
fi

# Create the script path
script_path="./rageval/article_generation/scripts/$domain/run_all.sh"

echo "Running script: $script_path"
bash $script_path
