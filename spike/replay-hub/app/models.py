"""Pydantic models for clip metadata."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ClipMetadata(BaseModel):
    """Metadata for a clip - free-form key-value pairs."""

    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Free-form metadata - users can add any fields they want
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClipInfo(BaseModel):
    """Combined model for displaying clip with metadata."""

    month: str
    filename: str
    webdav_path: str
    metadata: Optional[ClipMetadata] = None
    has_metadata: bool = False
    has_proxy: bool = False
    has_thumbnail: bool = False
