#!/bin/bash

# Check for config.json in kustomize app directories
echo "Checking for config.json files in kustomize directories..."

# Get root directory of the git repo
ROOT_DIR=$(git rev-parse --show-toplevel)

# Get all directories in the kustomize directory (excluding bootstrap-config.sh and node_modules)
directories=$(find "${ROOT_DIR}/deployment/kubernetes/kustomize" -mindepth 1 -maxdepth 1 -type d | grep -v "node_modules")

missing_configs=0
for dir in $directories; do
  # Skip if this is the bootstrap script
  if [[ "$(basename "$dir")" == "bootstrap-config.sh" ]]; then
    continue
  fi
  
  # Check if config.json exists
  if [ ! -f "$dir/config.json" ]; then
    echo "Error: Missing config.json in $dir"
    missing_configs=1
  fi
done

if [ $missing_configs -ne 0 ]; then
  echo "Pre-commit check failed: Missing config.json files in one or more kustomize directories."
  exit 1
fi

echo "All kustomize directories have config.json files."
exit 0