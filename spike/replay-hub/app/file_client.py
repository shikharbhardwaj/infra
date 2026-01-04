"""Abstract file client interface with WebDAV and local filesystem implementations."""

import abc
import io
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Optional, List
from urllib.parse import quote

import requests
from webdav3.client import Client

from app.config import settings

logger = logging.getLogger(__name__)


class FileClient(abc.ABC):
    """Abstract interface for file operations."""

    @staticmethod
    def create():
        """
        Factory method to create the appropriate file client based on settings.

        Returns:
            FileClient: Either WebDAVFileClient or LocalFileClient based on STORAGE_BACKEND setting
        """
        from app.config import settings

        if settings.storage_backend == "local":
            logger.info(f"Using LOCAL filesystem backend")
            return LocalFileClient()
        elif settings.storage_backend == "webdav":
            logger.info(f"Using WEBDAV backend")
            return WebDAVFileClient()
        else:
            raise ValueError(f"Unknown storage backend: {settings.storage_backend}")

    @abc.abstractmethod
    def list_directories(self, path: str = "") -> List[str]:
        """List directories in a given path."""
        pass

    @abc.abstractmethod
    def list_files(self, path: str = "", pattern: str = "*.mp4", exclude_proxy: bool = True) -> List[str]:
        """List files matching pattern in a given path."""
        pass

    @abc.abstractmethod
    def read_file(self, path: str) -> bytes:
        """Read file content."""
        pass

    @abc.abstractmethod
    def write_file(self, path: str, content: bytes):
        """Write file content."""
        pass

    @abc.abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        pass

    @abc.abstractmethod
    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        pass

    @abc.abstractmethod
    def read_file_range(self, path: str, start: int, end: int) -> bytes:
        """Read a range of bytes from a file (inclusive start, exclusive end)."""
        pass

    @abc.abstractmethod
    def ensure_directory(self, path: str):
        """Ensure a directory exists, creating it if necessary."""
        pass

    # Common helper methods (not abstract)
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


class WebDAVFileClient(FileClient):
    """WebDAV implementation of file client."""

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
        """List directories in a given path."""
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
        """List files matching pattern in a given path."""
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
        """Read file content from WebDAV."""
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
        """Ensure a directory exists, creating it if necessary."""
        full_path = self._full_path(path)
        try:
            if not self.client.check(full_path):
                self.client.mkdir(full_path)
                logger.info(f"Created directory: {full_path}")
        except Exception as e:
            logger.error(f"Error ensuring directory {full_path}: {e}")
            raise

    def write_file(self, path: str, content: bytes):
        """Write file content to WebDAV."""
        full_path = self._full_path(path)
        try:
            # Ensure parent directory exists
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
        """Check if file exists in WebDAV."""
        full_path = self._full_path(path)
        try:
            exists = self.client.check(full_path)
            logger.debug(f"File {full_path} exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error checking file existence {full_path}: {e}")
            return False

    def get_file_size(self, path: str) -> int:
        """Get file size in bytes from WebDAV."""
        full_path = self._full_path(path)
        try:
            info = self.client.info(full_path)
            size = int(info.get('size', 0))
            logger.debug(f"File {full_path} size: {size} bytes")
            return size
        except Exception as e:
            logger.error(f"Error getting file size {full_path}: {e}")
            raise

    def read_file_range(self, path: str, start: int, end: int) -> bytes:
        """Read a range of bytes from WebDAV file."""
        full_path = self._full_path(path)
        try:
            # WebDAV supports HTTP Range requests
            # Construct URL properly - the webdav_url already includes the base path
            # e.g., https://drive.shkhr.ovh/remote.php/dav/files/replay-hub/
            # So we just need to append the full_path
            base_url = settings.webdav_url.rstrip('/')
            # URL encode the path components but not the slashes
            encoded_path = '/'.join(quote(part, safe='') for part in full_path.split('/'))
            url = f"{base_url}/{encoded_path}"

            headers = {'Range': f'bytes={start}-{end-1}'}  # HTTP range is inclusive

            logger.debug(f"WebDAV Range Request URL: {url}")

            response = requests.get(
                url,
                headers=headers,
                auth=(settings.webdav_username, settings.webdav_password),
                stream=True
            )
            response.raise_for_status()

            content = response.content
            logger.debug(f"Read {len(content)} bytes (range {start}-{end}) from {full_path}")
            return content
        except Exception as e:
            logger.error(f"Error reading range {start}-{end} from {full_path}: {e}")
            raise


class LocalFileClient(FileClient):
    """Local filesystem implementation of file client."""

    def __init__(self, root_path: Optional[str] = None):
        """
        Initialize local file client.

        Args:
            root_path: Root directory for file operations (default: settings.local_root_path)
        """
        self.root_path = Path(root_path or settings.local_root_path).expanduser().resolve()
        logger.info(f"Initialized Local file client")
        logger.info(f"  Root path: '{self.root_path}'")

        # Ensure root path exists
        self.root_path.mkdir(parents=True, exist_ok=True)

    def _full_path(self, path: str) -> Path:
        """Convert relative path to full local path."""
        if not path or path == "/":
            return self.root_path

        # Remove leading slash if present
        if path.startswith("/"):
            path = path[1:]

        full_path = self.root_path / path
        logger.debug(f"Path conversion: '{path}' -> '{full_path}'")
        return full_path

    def list_directories(self, path: str = "") -> List[str]:
        """List directories in a given path."""
        full_path = self._full_path(path)
        logger.info(f"Listing directories at path='{path}' -> full_path='{full_path}'")
        try:
            if not full_path.exists():
                logger.warning(f"Path does not exist: {full_path}")
                return []

            dirs = [item.name for item in full_path.iterdir() if item.is_dir()]
            logger.info(f"Found {len(dirs)} directories in '{full_path}': {dirs}")
            return dirs
        except Exception as e:
            logger.error(f"Error listing directories in '{full_path}': {e}")
            return []

    def list_files(self, path: str = "", pattern: str = "*.mp4", exclude_proxy: bool = True) -> List[str]:
        """List files matching pattern in a given path."""
        full_path = self._full_path(path)
        logger.info(f"Listing files at path='{path}' -> full_path='{full_path}'")
        try:
            if not full_path.exists():
                logger.warning(f"Path does not exist: {full_path}")
                return []

            # Get all files
            files = [item.name for item in full_path.iterdir() if item.is_file()]

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
            return []

    def read_file(self, path: str) -> bytes:
        """Read file content from local filesystem."""
        full_path = self._full_path(path)
        try:
            content = full_path.read_bytes()
            logger.debug(f"Read {len(content)} bytes from {full_path}")
            return content
        except Exception as e:
            logger.error(f"Error reading file {full_path}: {e}")
            raise

    def ensure_directory(self, path: str):
        """Ensure a directory exists, creating it if necessary."""
        full_path = self._full_path(path)
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {full_path}")
        except Exception as e:
            logger.error(f"Error ensuring directory {full_path}: {e}")
            raise

    def write_file(self, path: str, content: bytes):
        """Write file content to local filesystem."""
        full_path = self._full_path(path)
        try:
            # Ensure parent directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)

            full_path.write_bytes(content)
            logger.info(f"Wrote {len(content)} bytes to {full_path}")
        except Exception as e:
            logger.error(f"Error writing file {full_path}: {e}")
            raise

    def file_exists(self, path: str) -> bool:
        """Check if file exists in local filesystem."""
        full_path = self._full_path(path)
        exists = full_path.exists() and full_path.is_file()
        logger.debug(f"File {full_path} exists: {exists}")
        return exists

    def get_file_size(self, path: str) -> int:
        """Get file size in bytes from local filesystem."""
        full_path = self._full_path(path)
        try:
            size = full_path.stat().st_size
            logger.debug(f"File {full_path} size: {size} bytes")
            return size
        except Exception as e:
            logger.error(f"Error getting file size {full_path}: {e}")
            raise

    def read_file_range(self, path: str, start: int, end: int) -> bytes:
        """Read a range of bytes from local file."""
        full_path = self._full_path(path)
        try:
            with open(full_path, 'rb') as f:
                f.seek(start)
                content = f.read(end - start)
            logger.debug(f"Read {len(content)} bytes (range {start}-{end}) from {full_path}")
            return content
        except Exception as e:
            logger.error(f"Error reading range {start}-{end} from {full_path}: {e}")
            raise
