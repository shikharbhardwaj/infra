"""Routes for metadata CRUD operations."""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse

from app.file_client import FileClient
from app.models import ClipMetadata

# Create file client based on configuration
file_client = FileClient.create()

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/clips/{month}/{filename:path}/metadata")
async def get_metadata(month: str, filename: str):
    """Retrieve metadata for a clip."""
    try:
        # URL decode the path (handles spaces and special characters)
        from urllib.parse import unquote
        month = unquote(month)
        filename = unquote(filename)

        video_path = f"{month}/{filename}"
        metadata_dict = file_client.read_metadata(video_path)

        if metadata_dict is None:
            return JSONResponse(
                status_code=404,
                content={"detail": "Metadata not found"}
            )

        return JSONResponse(content=metadata_dict)
    except Exception as e:
        logger.error(f"Error retrieving metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clips/{month}/{filename:path}/metadata")
async def save_metadata(month: str, filename: str, metadata: Dict[str, Any]):
    """Save or update metadata for a clip."""
    try:
        # URL decode the path (handles spaces and special characters)
        from urllib.parse import unquote
        month = unquote(month)
        filename = unquote(filename)

        video_path = f"{month}/{filename}"

        # Check if video exists
        if not file_client.file_exists(video_path):
            raise HTTPException(status_code=404, detail="Clip not found")

        # Load existing metadata or create new
        existing_metadata = file_client.read_metadata(video_path)

        if existing_metadata:
            # Update existing metadata
            clip_metadata = ClipMetadata(**existing_metadata)
            clip_metadata.metadata = metadata
            clip_metadata.updated_at = datetime.utcnow()
        else:
            # Create new metadata
            clip_metadata = ClipMetadata(metadata=metadata)

        # Save metadata
        file_client.write_metadata(video_path, clip_metadata.model_dump(mode='json'))

        return JSONResponse(
            content={
                "status": "success",
                "message": "Metadata saved successfully"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
