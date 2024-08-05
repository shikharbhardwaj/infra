import os
import json

import jsonschema
from jsonschema import validate

# Load JSON schema
schema_path = os.path.join(os.path.dirname(__file__), 'service.schema.json')
with open(schema_path, 'r') as schema_file:
    schema = json.load(schema_file)

def validate_config_file(file_path):
    with open(file_path, 'r') as data_file:
        data = json.load(data_file)
    try:
        validate(instance=data, schema=schema)
        print(f"{file_path} is valid.")
    except jsonschema.exceptions.ValidationError as err:
        print(f"Validation errors in {file_path}:")
        print(err)
        exit(1)

def find_config_files(dir_path):
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file == 'config.json':
                file_path = os.path.join(root, file)
                validate_config_file(file_path)

# Set the deployment directory
deployment_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
find_config_files(deployment_dir)
