#!/usr/bin/env python3
import json
import os
import pathlib


automation_dir_path = os.path.dirname(__file__)
deployment_dir_path = os.path.join(automation_dir_path, '..')

# Find all config.json files
all_configs = list(pathlib.Path(deployment_dir_path).rglob('config.json'))

# Parse the config.json files and print the service names
# where the "status" key is set to "live"
for config in all_configs:
    with open(config, 'r') as file:
        data = json.load(file)

    if data['status'] == 'live':
        service_path = config.parent
        accepted_variants = data['environment']
        variant_path = service_path / 'overlays'
        for variant in variant_path.glob(accepted_variants):
            print(f'{service_path.name} {variant.name}')