"""Routes for metadata CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import Dict, Any
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.database import metadata_db
from app.models import ClipMetadata

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/clips/{month}/{filename:path}/metadata")
async def get_metadata(month: str, filename: str):
    """Retrieve metadata for a clip."""
    try:
        month = unquote(month)
        filename = unquote(filename)

        clip_path = f"{month}/{filename}"
        metadata_dict = metadata_db.get_metadata(clip_path)

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
        month = unquote(month)
        filename = unquote(filename)

        clip_path = f"{month}/{filename}"

        # Load existing metadata or create new
        existing_metadata = metadata_db.get_metadata(clip_path)

        if existing_metadata:
            # Update existing metadata
            clip_metadata = ClipMetadata(**existing_metadata)
            clip_metadata.metadata = metadata
            clip_metadata.updated_at = datetime.now(timezone.utc)
        else:
            # Create new metadata
            clip_metadata = ClipMetadata(metadata=metadata)

        # Save metadata to database
        metadata_db.save_metadata(clip_path, clip_metadata.model_dump(mode='json'))

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
