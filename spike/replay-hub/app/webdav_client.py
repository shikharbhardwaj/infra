"""WebDAV client wrapper for Nextcloud storage operations."""

import io
import json
import logging
from typing import Optional, List
from webdav3.client import Client

from app.config import settings

logger = logging.getLogger(__name__)


class WebDAVClient:
    """Wrapper for WebDAV operations on Nextcloud storage."""

    def __init__(self):
        """Initialize WebDAV client with configured credentials."""
        self.client = Client({
            'webdav_hostname': settings.webdav_url,
            'webdav_login': settings.webdav_username,
            'webdav_password': settings.webdav_password,
        })
        self.root_path = settings.webdav_root_path
        logger.info(f"Initialized WebDAV client")
        logger.info(f"  URL: {settings.webdav_url}")
        logger.info(f"  Username: {settings.webdav_username}")
        logger.info(f"  Root path: '{settings.webdav_root_path}'")

    def _full_path(self, path: str) -> str:
        """Convert relative path to full WebDAV path."""
        original_path = path
        if path.startswith("/"):
            path = path[1:]

        # Handle empty root_path
        if not self.root_path or self.root_path == "/":
            result = path if path else "/"
            logger.debug(f"Path conversion: '{original_path}' -> '{result}' (root_path empty or /)")
            return result

        # Ensure root_path doesn't end with / unless it's just /
        root = self.root_path.rstrip('/')

        # Combine root and path
        if path:
            result = f"{root}/{path}"
        else:
            result = root

        logger.debug(f"Path conversion: '{original_path}' + root '{self.root_path}' -> '{result}'")
        return result

    def list_directories(self, path: str = "") -> List[str]:
        """
        List directories in a given path.

        Args:
            path: Relative path from root (default: root)

        Returns:
            List of directory names (without trailing /)
        """
        full_path = self._full_path(path)
        logger.info(f"Listing directories at path='{path}' -> full_path='{full_path}'")
        try:
            items = self.client.list(full_path)
            logger.debug(f"Raw items from WebDAV: {items}")
            # Filter directories (end with /) and remove current directory
            dirs = [item.rstrip('/') for item in items if item.endswith('/') and item != './']
            logger.info(f"Found {len(dirs)} directories in '{full_path}': {dirs}")
            return dirs
        except Exception as e:
            logger.error(f"Error listing directories in '{full_path}': {e}")
            logger.error(f"  Input path: '{path}'")
            logger.error(f"  Root path: '{self.root_path}'")
            return []

    def list_files(self, path: str = "", pattern: str = "*.mp4", exclude_proxy: bool = True) -> List[str]:
        """
        List files matching pattern in a given path.

        Args:
            path: Relative path from root
            pattern: File pattern to match (default: *.mp4)
            exclude_proxy: Exclude proxy files (_proxy.mp4) (default: True)

        Returns:
            List of filenames
        """
        full_path = self._full_path(path)
        logger.info(f"Listing files at path='{path}' -> full_path='{full_path}'")
        try:
            items = self.client.list(full_path)
            logger.debug(f"Raw items from WebDAV: {items}")
            # Filter files (don't end with /)
            files = [item for item in items if not item.endswith('/') and item != './']

            # Apply pattern filter
            if pattern:
                ext = pattern.replace("*", "")
                files = [f for f in files if f.endswith(ext)]

            # Exclude proxy files if requested
            if exclude_proxy:
                proxy_suffix = f"{settings.proxy_suffix}.mp4"
                files = [f for f in files if not f.endswith(proxy_suffix)]
                logger.debug(f"Excluded proxy files with suffix '{proxy_suffix}'")

            logger.info(f"Found {len(files)} files in '{full_path}': {files[:5]}{'...' if len(files) > 5 else ''}")
            return files
        except Exception as e:
            logger.error(f"Error listing files in '{full_path}': {e}")
            logger.error(f"  Input path: '{path}'")
            logger.error(f"  Root path: '{self.root_path}'")
            logger.error(f"  Pattern: '{pattern}'")
            return []

    def read_file(self, path: str) -> bytes:
        """
        Read file content from WebDAV.

        Args:
            path: Relative path to file

        Returns:
            File content as bytes
        """
        full_path = self._full_path(path)
        try:
            buffer = io.BytesIO()
            self.client.download_from(buffer, full_path)
            content = buffer.getvalue()
            logger.debug(f"Read {len(content)} bytes from {full_path}")
            return content
        except Exception as e:
            logger.error(f"Error reading file {full_path}: {e}")
            raise

    def ensure_directory(self, path: str):
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: Relative path to directory
        """
        full_path = self._full_path(path)
        try:
            if not self.client.check(full_path):
                self.client.mkdir(full_path)
                logger.info(f"Created directory: {full_path}")
        except Exception as e:
            logger.error(f"Error ensuring directory {full_path}: {e}")
            raise

    def write_file(self, path: str, content: bytes):
        """
        Write file content to WebDAV.
        Automatically creates parent directory if it doesn't exist.

        Args:
            path: Relative path to file
            content: File content as bytes
        """
        full_path = self._full_path(path)
        try:
            # Ensure parent directory exists
            import os
            parent_dir = os.path.dirname(path)
            if parent_dir:
                self.ensure_directory(parent_dir)

            buffer = io.BytesIO(content)
            self.client.upload_to(buffer, full_path)
            logger.info(f"Wrote {len(content)} bytes to {full_path}")
        except Exception as e:
            logger.error(f"Error writing file {full_path}: {e}")
            raise

    def file_exists(self, path: str) -> bool:
        """
        Check if file exists.

        Args:
            path: Relative path to file

        Returns:
            True if file exists, False otherwise
        """
        full_path = self._full_path(path)
        try:
            exists = self.client.check(full_path)
            logger.debug(f"File {full_path} exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error checking file existence {full_path}: {e}")
            return False

    def get_metadata_path(self, video_path: str) -> str:
        """
        Get metadata file path for a video.

        Metadata is stored in a 'metadata/' folder at the same level as 'proxies/'.
        For example:
            video_path: "2024-11/proxies/clip_proxy.mp4"
            metadata: "2024-11/metadata/clip.mp4.metadata.json"

        Args:
            video_path: Path to video file (e.g., "2024-11/proxies/clip_proxy.mp4")

        Returns:
            Path to metadata JSON file
        """
        import os

        # Extract components: "2024-11/proxies/clip_proxy.mp4"
        parts = video_path.split('/')

        if len(parts) >= 3 and parts[-2] == 'proxies':
            # Structure: month/proxies/filename
            month = '/'.join(parts[:-2])  # "2024-11"
            filename = parts[-1]  # "clip_proxy.mp4"

            # Strip _proxy suffix from filename
            if filename.endswith(f"{settings.proxy_suffix}.mp4"):
                filename = filename[:-len(f"{settings.proxy_suffix}.mp4")] + ".mp4"

            # Build metadata path: month/metadata/filename.metadata.json
            return f"{month}/metadata/{filename}.metadata.json"
        else:
            # Fallback: old behavior (store metadata alongside video)
            return f"{video_path}.metadata.json"

    def get_display_name(self, filename: str) -> str:
        """
        Get display name for a video file (strip _proxy suffix).

        Args:
            filename: Video filename (e.g., "clip_proxy.mp4")

        Returns:
            Display name without proxy suffix (e.g., "clip.mp4")
        """
        if filename.endswith(f"{settings.proxy_suffix}.mp4"):
            return filename[:-len(f"{settings.proxy_suffix}.mp4")] + ".mp4"
        return filename

    def get_proxy_path(self, video_path: str) -> str:
        """
        Get proxy video path for a video.

        Args:
            video_path: Path to video file (e.g., "2024-11/clip.mp4")

        Returns:
            Path to proxy video file
        """
        # Replace .mp4 with _proxy.mp4
        if video_path.endswith('.mp4'):
            return video_path[:-4] + f"{settings.proxy_suffix}.mp4"
        return video_path + settings.proxy_suffix

    def read_metadata(self, video_path: str) -> Optional[dict]:
        """
        Read metadata JSON for a video.

        Args:
            video_path: Relative path to video file

        Returns:
            Metadata dict or None if not found
        """
        metadata_path = self.get_metadata_path(video_path)
        if not self.file_exists(metadata_path):
            logger.debug(f"No metadata found for {video_path}")
            return None

        try:
            content = self.read_file(metadata_path)
            metadata = json.loads(content.decode('utf-8'))
            logger.debug(f"Loaded metadata for {video_path}")
            return metadata
        except Exception as e:
            logger.error(f"Error reading metadata for {video_path}: {e}")
            return None

    def write_metadata(self, video_path: str, metadata: dict):
        """
        Write metadata JSON for a video.

        Args:
            video_path: Relative path to video file
            metadata: Metadata dictionary to save
        """
        metadata_path = self.get_metadata_path(video_path)
        try:
            content = json.dumps(metadata, indent=2, default=str).encode('utf-8')
            self.write_file(metadata_path, content)
            logger.info(f"Saved metadata for {video_path}")
        except Exception as e:
            logger.error(f"Error writing metadata for {video_path}: {e}")
            raise


# Global WebDAV client instance
webdav_client = WebDAVClient()
