#!/bin/bash

# Base folder path
BASE_FOLDER=`pwd`

# Loop through each subfolder in the base folder
for SUBFOLDER in "$BASE_FOLDER"/*; do
    if [ -d "$SUBFOLDER" ]; then
        # Get the folder name
        FOLDER_NAME=$(basename "$SUBFOLDER")
        
        # Create the JSON content
        JSON_CONTENT=$(cat <<EOF
{
    "name": "$FOLDER_NAME",
    "type": "k8s-kustomize",
    "environment": "dev",
    "status": "live"
}
EOF
)
        
        # Define the JSON file path
        JSON_FILE_PATH="$SUBFOLDER/config.json"
        
        # Write the JSON content to the file
        echo "$JSON_CONTENT" > "$JSON_FILE_PATH"
        
        echo "Created $JSON_FILE_PATH"
    fi
done

echo "JSON files created in all subfolders."

