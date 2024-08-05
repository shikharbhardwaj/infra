#!/bin/bash

set -eou pipefail

# Get current script dir.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DEPLOYMENT_DIR="$(dirname $SCRIPT_DIR)"

targets="$($SCRIPT_DIR/list-live-targets.py)"

while IFS= read -r target; do
    # Get service and variants by splitting the targets string.
    app=$(echo $target | cut -d ' ' -f1)
    variant=$(echo $target | cut -d ' ' -f2)
    echo "Deploying $app to $variant"
    make -C deployment/kubernetes deploy app=$app variant=$variant
done <<< "$targets"