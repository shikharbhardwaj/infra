"""Routes for browsing and viewing clips."""

import logging
from typing import List
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
import io

from app.webdav_client import webdav_client
from app.models import ClipInfo, ClipMetadata

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def index(request: Request):
    """Homepage with clip grid grouped by month."""
    try:
        # List month directories
        months = webdav_client.list_directories()
        months.sort(reverse=True)  # Most recent first

        # Get clips for each month
        clips_by_month = {}
        for month in months:
            # List files from the proxies subdirectory within each month
            proxy_dir = f"{month}/proxies"
            files = webdav_client.list_files(proxy_dir, pattern="*.mp4", exclude_proxy=False)

            clips = []
            for filename in files:
                # Full path includes the proxies subdirectory
                video_path = f"{proxy_dir}/{filename}"
                metadata_dict = webdav_client.read_metadata(video_path)
                has_metadata = metadata_dict is not None

                # Check for proxy
                proxy_path = webdav_client.get_proxy_path(video_path)
                has_proxy = webdav_client.file_exists(proxy_path)

                # Parse metadata if exists
                metadata = None
                if metadata_dict:
                    try:
                        metadata = ClipMetadata(**metadata_dict)
                    except Exception as e:
                        logger.error(f"Error parsing metadata for {video_path}: {e}")

                clip_info = ClipInfo(
                    month=month,
                    filename=filename,
                    webdav_path=video_path,
                    metadata=metadata,
                    has_metadata=has_metadata,
                    has_proxy=has_proxy
                )
                clips.append(clip_info)

            if clips:
                clips_by_month[month] = clips

        return templates.TemplateResponse(
            "index.html",
            {"request": request, "clips_by_month": clips_by_month}
        )
    except Exception as e:
        logger.error(f"Error loading index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clips/{month}/{subpath:path}")
async def clip_detail(request: Request, month: str, subpath: str):
    """Clip detail view with video player and metadata form."""
    try:
        # subpath will be "proxies/filename.mp4"
        video_path = f"{month}/{subpath}"

        # Extract just the filename for display
        import os
        filename = os.path.basename(subpath)

        # Check if video exists
        if not webdav_client.file_exists(video_path):
            raise HTTPException(status_code=404, detail="Clip not found")

        # Load metadata
        metadata_dict = webdav_client.read_metadata(video_path)
        metadata = None
        if metadata_dict:
            try:
                metadata = ClipMetadata(**metadata_dict)
            except Exception as e:
                logger.error(f"Error parsing metadata for {video_path}: {e}")

        # Check for proxy (though the file itself is already a proxy)
        from app.config import settings
        is_already_proxy = filename.endswith(f"{settings.proxy_suffix}.mp4")
        has_proxy = is_already_proxy

        clip_info = ClipInfo(
            month=month,
            filename=filename,
            webdav_path=video_path,
            metadata=metadata,
            has_metadata=metadata is not None,
            has_proxy=has_proxy
        )

        return templates.TemplateResponse(
            "clip_detail.html",
            {"request": request, "clip": clip_info}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading clip detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clips/{month}/{subpath:path}/stream")
async def stream_video(month: str, subpath: str):
    """Stream video file from WebDAV."""
    try:
        # subpath will be "proxies/filename.mp4"
        video_path = f"{month}/{subpath}"

        # Extract filename for proxy check
        import os
        filename = os.path.basename(subpath)

        # Only try proxy if the file itself is not already a proxy
        from app.config import settings
        is_already_proxy = filename.endswith(f"{settings.proxy_suffix}.mp4")

        if not is_already_proxy:
            # Try proxy first if available
            proxy_path = webdav_client.get_proxy_path(video_path)
            if webdav_client.file_exists(proxy_path):
                video_path = proxy_path

        # Check if video exists
        if not webdav_client.file_exists(video_path):
            raise HTTPException(status_code=404, detail="Video not found")

        # Download video
        video_data = webdav_client.read_file(video_path)

        return StreamingResponse(
            io.BytesIO(video_data),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(len(video_data))
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming video: {e}")
        raise HTTPException(status_code=500, detail=str(e))
