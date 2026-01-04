"""Routes for browsing and viewing clips."""

import io
import logging
import os
import re
from pathlib import Path
from typing import List
from urllib.parse import unquote

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from app.file_client import FileClient
from app.models import ClipInfo, ClipMetadata
from app.config import settings

# Create file client based on configuration
file_client = FileClient.create()

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def index(request: Request):
    """Homepage with clip grid grouped by month."""
    try:
        # List month directories
        months = file_client.list_directories()
        months.sort(reverse=True)  # Most recent first

        # Get clips for each month
        clips_by_month = {}
        for month in months:
            # List files from the proxies subdirectory within each month
            proxy_dir = f"{month}/proxies"

            # OPTIMIZATION: List all files once
            # List proxy videos
            proxy_files = file_client.list_files(proxy_dir, pattern="", exclude_proxy=False)
            video_files = [f for f in proxy_files if f.endswith('.mp4')]

            # List metadata files from the metadata folder
            metadata_dir = f"{month}/metadata"
            metadata_files = set()
            try:
                metadata_list = file_client.list_files(metadata_dir, pattern="", exclude_proxy=False)
                metadata_files = set(f for f in metadata_list if f.endswith('.metadata.json'))
            except Exception:
                # Metadata folder might not exist yet
                pass

            # List thumbnail files from the thumbnails folder
            thumbnails_dir = f"{month}/thumbnails"
            thumbnail_files = set()
            try:
                thumbnail_list = file_client.list_files(thumbnails_dir, pattern="", exclude_proxy=False)
                thumbnail_files = set(f for f in thumbnail_list if f.endswith('.jpg'))
            except Exception:
                # Thumbnails folder might not exist yet
                pass

            clips = []
            for filename in video_files:
                # Full path includes the proxies subdirectory
                video_path = f"{proxy_dir}/{filename}"

                # Get display name (strip _proxy suffix)
                display_name = file_client.get_display_name(filename)

                # Check if metadata exists (fast - no WebDAV request)
                metadata_filename = f"{display_name}.metadata.json"
                has_metadata = metadata_filename in metadata_files

                # Check if thumbnail exists
                # Thumbnails are named: {filename_without_ext}_proxy.jpg
                # e.g., "Counter-strike 2 2023.07.19 - 16.23.00.02.DVR_proxy.jpg"
                display_name_stem = Path(display_name).stem
                thumbnail_filename = f"{display_name_stem}{settings.proxy_suffix}.jpg"
                has_thumbnail = thumbnail_filename in thumbnail_files

                # Since all files are proxies, has_proxy is always True
                has_proxy = True

                clip_info = ClipInfo(
                    month=month,
                    filename=display_name,  # Use display name instead of proxy filename
                    webdav_path=video_path,
                    metadata=None,  # Don't load metadata content on index (lazy load)
                    has_metadata=has_metadata,
                    has_proxy=has_proxy,
                    has_thumbnail=has_thumbnail
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
async def stream_video(request: Request, month: str, subpath: str):
    """Stream video file with proper range request support."""
    try:
        logger.info(f"Stream - Raw: month='{month}', subpath='{subpath}'")
        month = unquote(month)
        subpath = unquote(subpath)
        logger.info(f"Stream - Decoded: month='{month}', subpath='{subpath}'")

        # subpath will be "proxies/filename.mp4"
        video_path = f"{month}/{subpath}"
        logger.info(f"Stream - Full path: '{video_path}'")

        # Extract filename for proxy check
        filename = os.path.basename(subpath)

        # Only try proxy if the file itself is not already a proxy
        is_already_proxy = filename.endswith(f"{settings.proxy_suffix}.mp4")

        if not is_already_proxy:
            # Try proxy first if available
            proxy_path = file_client.get_proxy_path(video_path)
            if file_client.file_exists(proxy_path):
                video_path = proxy_path

        # Check if video exists
        logger.info(f"Stream - Checking exists: '{video_path}'")
        if not file_client.file_exists(video_path):
            logger.error(f"Stream - NOT FOUND: '{video_path}'")
            raise HTTPException(status_code=404, detail=f"Video not found: {video_path}")

        # Get file size
        file_size = file_client.get_file_size(video_path)

        # Parse Range header
        range_header = request.headers.get('range')

        # Determine range to serve
        if range_header:
            # Explicit range request from browser (e.g., seeking)
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else file_size - 1
                end = min(end, file_size - 1)
            else:
                # Invalid range format, serve initial chunk
                start = 0
                end = min(5 * 1024 * 1024 - 1, file_size - 1)  # 5MB initial chunk
        else:
            # No range header - initial request
            # Return first 5MB to enable quick playback start
            # Browser will request more via range requests as needed
            start = 0
            chunk_size = 5 * 1024 * 1024  # 5MB initial buffer
            end = min(chunk_size - 1, file_size - 1)
            logger.info(f"Stream - Initial request, serving first {chunk_size / 1024 / 1024:.1f}MB")

        # Read the requested range
        chunk = file_client.read_file_range(video_path, start, end + 1)

        logger.info(f"Stream - Range: {start}-{end}/{file_size} ({len(chunk)} bytes)")

        return StreamingResponse(
            io.BytesIO(chunk),
            status_code=206,  # Partial Content
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(len(chunk)),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clips/{month}/{filename:path}/thumbnail")
async def get_thumbnail(month: str, filename: str):
    """Serve thumbnail image for a clip."""
    try:
        logger.info(f"Thumbnail - Raw: month='{month}', filename='{filename}'")
        month = unquote(month)
        filename = unquote(filename)
        logger.info(f"Thumbnail - Decoded: month='{month}', filename='{filename}'")

        # Construct thumbnail path - filename is the display name with .mp4 extension
        # Need to strip .mp4 and add _proxy.jpg
        # Example: "Counter-strike 2 2023.07.19 - 16.23.00.02.DVR.mp4" -> "Counter-strike 2 2023.07.19 - 16.23.00.02.DVR_proxy.jpg"
        filename_stem = Path(filename).stem
        thumbnail_path = f"{month}/thumbnails/{filename_stem}{settings.proxy_suffix}.jpg"
        logger.info(f"Thumbnail - Looking for: '{thumbnail_path}'")

        # Check if thumbnail exists
        if not file_client.file_exists(thumbnail_path):
            logger.error(f"Thumbnail - NOT FOUND: '{thumbnail_path}'")

            # Debug: list what's in the thumbnails directory
            thumbnails_dir = f"{month}/thumbnails"
            try:
                files = file_client.list_files(thumbnails_dir, pattern="", exclude_proxy=False)
                logger.error(f"Thumbnail - Files in {thumbnails_dir}: {files[:5]}")
            except Exception as e:
                logger.error(f"Thumbnail - Error listing directory: {e}")

            raise HTTPException(status_code=404, detail="Thumbnail not found")

        # Read thumbnail file
        thumbnail_data = file_client.read_file(thumbnail_path)
        logger.info(f"Thumbnail - Successfully read {len(thumbnail_data)} bytes")

        return StreamingResponse(
            io.BytesIO(thumbnail_data),
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving thumbnail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clips/{month}/{subpath:path}")
async def clip_detail(request: Request, month: str, subpath: str):
    """Clip detail view with video player and metadata form."""
    try:
        logger.info(f"Detail - Raw: month='{month}', subpath='{subpath}'")
        month = unquote(month)
        subpath = unquote(subpath)
        logger.info(f"Detail - Decoded: month='{month}', subpath='{subpath}'")

        # subpath will be "proxies/filename_proxy.mp4"
        video_path = f"{month}/{subpath}"
        logger.info(f"Detail - Full path: '{video_path}'")

        # Extract just the filename and get display name (strip _proxy suffix)
        proxy_filename = os.path.basename(subpath)
        filename = file_client.get_display_name(proxy_filename)

        # Check if video exists
        logger.info(f"Detail - Checking exists: '{video_path}'")
        if not file_client.file_exists(video_path):
            logger.error(f"Detail - NOT FOUND: '{video_path}'")

            # Let's list what IS in that directory to help debug
            dir_path = os.path.dirname(video_path)
            logger.error(f"Detail - Listing directory: '{dir_path}'")
            try:
                files = file_client.list_files(dir_path, pattern="", exclude_proxy=False)
                logger.error(f"Detail - Files in directory: {files[:10]}")
            except Exception as e:
                logger.error(f"Detail - Error listing directory: {e}")

            raise HTTPException(status_code=404, detail=f"Clip not found: {video_path}")

        # Load metadata
        metadata_dict = file_client.read_metadata(video_path)
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
