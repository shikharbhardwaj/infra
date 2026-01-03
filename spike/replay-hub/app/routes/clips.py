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

            # OPTIMIZATION: List all files once
            # List proxy videos
            proxy_files = webdav_client.list_files(proxy_dir, pattern="", exclude_proxy=False)
            video_files = [f for f in proxy_files if f.endswith('.mp4')]

            # List metadata files from the metadata folder
            metadata_dir = f"{month}/metadata"
            metadata_files = set()
            try:
                metadata_list = webdav_client.list_files(metadata_dir, pattern="", exclude_proxy=False)
                metadata_files = set(f for f in metadata_list if f.endswith('.metadata.json'))
            except Exception:
                # Metadata folder might not exist yet
                pass

            clips = []
            for filename in video_files:
                # Full path includes the proxies subdirectory
                video_path = f"{proxy_dir}/{filename}"

                # Get display name (strip _proxy suffix)
                display_name = webdav_client.get_display_name(filename)

                # Check if metadata exists (fast - no WebDAV request)
                metadata_filename = f"{display_name}.metadata.json"
                has_metadata = metadata_filename in metadata_files

                # Since all files are proxies, has_proxy is always True
                has_proxy = True

                clip_info = ClipInfo(
                    month=month,
                    filename=display_name,  # Use display name instead of proxy filename
                    webdav_path=video_path,
                    metadata=None,  # Don't load metadata content on index (lazy load)
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


@router.get("/clips/{month}/{subpath:path}/stream")
async def stream_video(month: str, subpath: str):
    """Stream video file from WebDAV."""
    try:
        # URL decode the path (handles spaces and special characters)
        from urllib.parse import unquote
        logger.info(f"Stream - Raw: month='{month}', subpath='{subpath}'")
        month = unquote(month)
        subpath = unquote(subpath)
        logger.info(f"Stream - Decoded: month='{month}', subpath='{subpath}'")

        # subpath will be "proxies/filename.mp4"
        video_path = f"{month}/{subpath}"
        logger.info(f"Stream - Full path: '{video_path}'")

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
        logger.info(f"Stream - Checking exists: '{video_path}'")
        if not webdav_client.file_exists(video_path):
            logger.error(f"Stream - NOT FOUND: '{video_path}'")
            raise HTTPException(status_code=404, detail=f"Video not found: {video_path}")

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


@router.get("/clips/{month}/{subpath:path}")
async def clip_detail(request: Request, month: str, subpath: str):
    """Clip detail view with video player and metadata form."""
    try:
        # URL decode the path (handles spaces and special characters)
        from urllib.parse import unquote
        import os
        logger.info(f"Detail - Raw: month='{month}', subpath='{subpath}'")
        month = unquote(month)
        subpath = unquote(subpath)
        logger.info(f"Detail - Decoded: month='{month}', subpath='{subpath}'")

        # subpath will be "proxies/filename_proxy.mp4"
        video_path = f"{month}/{subpath}"
        logger.info(f"Detail - Full path: '{video_path}'")

        # Extract just the filename and get display name (strip _proxy suffix)
        proxy_filename = os.path.basename(subpath)
        filename = webdav_client.get_display_name(proxy_filename)

        # Check if video exists
        logger.info(f"Detail - Checking exists: '{video_path}'")
        if not webdav_client.file_exists(video_path):
            logger.error(f"Detail - NOT FOUND: '{video_path}'")

            # Let's list what IS in that directory to help debug
            dir_path = os.path.dirname(video_path)
            logger.error(f"Detail - Listing directory: '{dir_path}'")
            try:
                files = webdav_client.list_files(dir_path, pattern="", exclude_proxy=False)
                logger.error(f"Detail - Files in directory: {files[:10]}")
            except Exception as e:
                logger.error(f"Detail - Error listing directory: {e}")

            raise HTTPException(status_code=404, detail=f"Clip not found: {video_path}")

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
