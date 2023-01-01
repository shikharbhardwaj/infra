#!/bin/bash

cur_date="$(date +%F)"
base_dir="inflight/$cur_date"
mkdir -p "$base_dir"

services=(gitea bitwarden infra)

for service in "${services[@]}"; do
    mkdir -p "$base_dir/$service"
done
