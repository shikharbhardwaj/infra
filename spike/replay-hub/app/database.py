"""SQLite database for clip metadata storage."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.config import settings

logger = logging.getLogger(__name__)


class MetadataDB:
    """SQLite database for storing clip metadata."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.database_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            # Table for storing all discovered clips
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clip_path TEXT UNIQUE NOT NULL,
                    month TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    proxy_path TEXT,
                    has_thumbnail INTEGER DEFAULT 0,
                    discovered_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_clips_month ON clips(month)")

            # Table for clip metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clip_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clip_path TEXT UNIQUE NOT NULL,
                    month TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    version TEXT DEFAULT '1.0',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,

                    -- Default metadata fields for fast queries
                    map TEXT,
                    rating INTEGER,
                    description TEXT,
                    clip_type TEXT,

                    -- Additional metadata stored as JSON
                    extra_metadata TEXT DEFAULT '{}'
                )
            """)

            # Create indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_month ON clip_metadata(month)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_clip_type ON clip_metadata(clip_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rating ON clip_metadata(rating)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_map ON clip_metadata(map)")

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ==================== Clips Table Methods ====================

    def add_clip(self, month: str, filename: str, proxy_path: str, has_thumbnail: bool = False) -> bool:
        """Add or update a clip in the database."""
        clip_path = f"{month}/{filename}"
        now = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO clips (clip_path, month, filename, proxy_path, has_thumbnail, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(clip_path) DO UPDATE SET
                    proxy_path = excluded.proxy_path,
                    has_thumbnail = excluded.has_thumbnail
            """, (clip_path, month, filename, proxy_path, 1 if has_thumbnail else 0, now))
            conn.commit()
        return True

    def get_clips_for_month(
        self,
        month: str,
        clip_type: Optional[str] = None,
        min_rating: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all clips for a given month with their metadata status."""
        conditions = ["c.month = ?"]
        params = [month]

        if clip_type:
            conditions.append("m.clip_type = ?")
            params.append(clip_type)

        if min_rating is not None:
            conditions.append("m.rating >= ?")
            params.append(min_rating)

        where_clause = " AND ".join(conditions)

        with self._get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT
                    c.clip_path,
                    c.month,
                    c.filename,
                    c.proxy_path,
                    c.has_thumbnail,
                    CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as has_metadata,
                    m.map,
                    m.rating,
                    m.description,
                    m.clip_type
                FROM clips c
                LEFT JOIN clip_metadata m ON c.clip_path = m.clip_path
                WHERE {where_clause}
                ORDER BY c.filename DESC
            """, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_all_months(self) -> List[str]:
        """Get all months that have clips, sorted descending."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT month FROM clips ORDER BY month DESC
            """)
            return [row['month'] for row in cursor.fetchall()]

    def update_clip_thumbnail(self, clip_path: str, has_thumbnail: bool) -> bool:
        """Update thumbnail status for a clip."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE clips SET has_thumbnail = ? WHERE clip_path = ?
            """, (1 if has_thumbnail else 0, clip_path))
            conn.commit()
        return True

    def clip_exists(self, clip_path: str) -> bool:
        """Check if a clip exists in the database."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM clips WHERE clip_path = ?", (clip_path,)
            )
            return cursor.fetchone() is not None

    # ==================== Metadata Table Methods ====================

    def get_metadata(self, clip_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a clip by its path."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM clip_metadata WHERE clip_path = ?",
                (clip_path,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_dict(row)

    def save_metadata(self, clip_path: str, metadata: Dict[str, Any]) -> bool:
        """Save or update metadata for a clip."""
        # Extract month and filename from clip_path
        parts = clip_path.split('/', 1)
        month = parts[0] if len(parts) > 0 else ""
        filename = parts[1] if len(parts) > 1 else clip_path

        # Get the user metadata (the actual fields)
        user_metadata = metadata.get('metadata', {})

        # Extract default fields
        map_val = user_metadata.get('map')
        rating = user_metadata.get('rating')
        description = user_metadata.get('description')
        clip_type = user_metadata.get('clip_type')

        # Store remaining fields in extra_metadata
        default_fields = {'map', 'rating', 'description', 'clip_type'}
        extra = {k: v for k, v in user_metadata.items() if k not in default_fields}

        now = datetime.utcnow().isoformat()
        version = metadata.get('version', '1.0')
        created_at = metadata.get('created_at', now)
        updated_at = now

        # Convert rating to int if it's a string
        if rating is not None:
            try:
                rating = int(rating) if rating != '' else None
            except (ValueError, TypeError):
                rating = None

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO clip_metadata
                    (clip_path, month, filename, version, created_at, updated_at,
                     map, rating, description, clip_type, extra_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(clip_path) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    map = excluded.map,
                    rating = excluded.rating,
                    description = excluded.description,
                    clip_type = excluded.clip_type,
                    extra_metadata = excluded.extra_metadata
            """, (
                clip_path, month, filename, version, created_at, updated_at,
                map_val, rating, description, clip_type, json.dumps(extra)
            ))
            conn.commit()

        return True

    def delete_metadata(self, clip_path: str) -> bool:
        """Delete metadata for a clip."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM clip_metadata WHERE clip_path = ?",
                (clip_path,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_clips_with_metadata(self, month: Optional[str] = None) -> List[str]:
        """Get list of clip paths that have metadata."""
        with self._get_connection() as conn:
            if month:
                cursor = conn.execute(
                    "SELECT clip_path FROM clip_metadata WHERE month = ?",
                    (month,)
                )
            else:
                cursor = conn.execute("SELECT clip_path FROM clip_metadata")

            return [row['clip_path'] for row in cursor.fetchall()]

    def get_metadata_filenames_for_month(self, month: str) -> set:
        """Get set of filenames that have metadata for a given month."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT filename FROM clip_metadata WHERE month = ?",
                (month,)
            )
            return {row['filename'] for row in cursor.fetchall()}

    def search_metadata(
        self,
        query: Optional[str] = None,
        clip_type: Optional[str] = None,
        min_rating: Optional[int] = None,
        map_name: Optional[str] = None,
        month: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search metadata with filters."""
        conditions = []
        params = []

        if query:
            conditions.append("(filename LIKE ? OR description LIKE ? OR map LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])

        if clip_type:
            conditions.append("clip_type = ?")
            params.append(clip_type)

        if min_rating is not None:
            conditions.append("rating >= ?")
            params.append(min_rating)

        if map_name:
            conditions.append("map LIKE ?")
            params.append(f"%{map_name}%")

        if month:
            conditions.append("month = ?")
            params.append(month)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"SELECT * FROM clip_metadata WHERE {where_clause} ORDER BY updated_at DESC LIMIT ?",
                params
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a metadata dictionary."""
        extra = json.loads(row['extra_metadata'] or '{}')

        # Reconstruct the metadata dict
        user_metadata = {}
        if row['map']:
            user_metadata['map'] = row['map']
        if row['rating'] is not None:
            user_metadata['rating'] = row['rating']
        if row['description']:
            user_metadata['description'] = row['description']
        if row['clip_type']:
            user_metadata['clip_type'] = row['clip_type']

        # Add extra fields
        user_metadata.update(extra)

        return {
            'version': row['version'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'metadata': user_metadata
        }


# Global database instance
metadata_db = MetadataDB()
