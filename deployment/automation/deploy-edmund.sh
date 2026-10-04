#!/bin/bash
# Deploy every app under deployment/talos/edmund/apps/ to edmund - called by
# .github/workflows/cd-edmund.yml. Each app dir is a kustomization rendered
# through the ansible vault (see deployment/kubernetes/Makefile edmund-deploy).
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

for app_dir in "$REPO_DIR"/deployment/talos/edmund/apps/*/; do
    [[ -f "$app_dir/kustomization.yaml" ]] || continue
    app=$(basename "$app_dir")
    echo "Deploying $app to edmund"
    make -C "$REPO_DIR/deployment/kubernetes" edmund-deploy app="$app"
done
