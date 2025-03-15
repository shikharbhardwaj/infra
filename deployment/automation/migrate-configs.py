#!/usr/bin/env python3
import json
import os
import pathlib

automation_dir_path = os.path.dirname(__file__)
deployment_dir_path = os.path.join(automation_dir_path, '..')

# Find all config.json files
all_configs = list(pathlib.Path(deployment_dir_path).rglob('config.json'))

# Parse and update the config.json files
for config in all_configs:
    with open(config, 'r') as file:
        data = json.load(file)
    
    # Skip if already migrated
    if 'environments' in data:
        continue
    
    # Migrate from old to new format
    if 'environment' in data and 'status' in data:
        env_name = data['environment']
        env_status = data['status']
        
        # Create new format
        data['environments'] = [
            {
                'name': env_name,
                'status': env_status
            }
        ]
        
        # Remove old keys
        del data['environment']
        del data['status']
        
        # Write back to file
        with open(config, 'w') as file:
            json.dump(data, file, indent=4)
        
        print(f"Migrated {config}")

print("Migration complete")