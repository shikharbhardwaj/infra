"""Routes for metadata CRUD operations."""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import metadata_db
from app.models import ClipMetadata

logger = logging.getLogger(__name__)
router = APIRouter()


def normalize_clip_path(month: str, filename: str) -> str:
    """
    Normalize a clip path to match the format used in the clips table.

    The clips table stores paths as "{month}/{display_name}" (e.g., "2024-11/clip.mp4"),
    but requests may come with proxy paths like "proxies/clip_proxy.mp4".

    Args:
        month: The month directory (e.g., "2024-11")
        filename: The filename, possibly including subdirectory (e.g., "proxies/clip_proxy.mp4")

    Returns:
        Normalized clip path (e.g., "2024-11/clip.mp4")
    """
    # Extract just the filename, stripping any subdirectory like "proxies/"
    basename = os.path.basename(filename)

    # Convert proxy filename to display name (strip _proxy suffix)
    if basename.endswith(f"{settings.proxy_suffix}.mp4"):
        display_name = basename[: -len(f"{settings.proxy_suffix}.mp4")] + ".mp4"
    else:
        display_name = basename

    return f"{month}/{display_name}"


@router.get("/clips/{month}/{filename:path}/metadata")
async def get_metadata(month: str, filename: str):
    """Retrieve metadata for a clip."""
    try:
        month = unquote(month)
        filename = unquote(filename)

        clip_path = normalize_clip_path(month, filename)
        metadata_dict = metadata_db.get_metadata(clip_path)

        if metadata_dict is None:
            return JSONResponse(
                status_code=404, content={"detail": "Metadata not found"}
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

        clip_path = normalize_clip_path(month, filename)

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
        metadata_db.save_metadata(clip_path, clip_metadata.model_dump(mode="json"))

        return JSONResponse(
            content={"status": "success", "message": "Metadata saved successfully"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
