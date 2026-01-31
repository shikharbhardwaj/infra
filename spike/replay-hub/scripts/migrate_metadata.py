#!/usr/bin/env python3
"""
Scan clips and migrate metadata from JSON files to SQLite database.

Usage:
    python scripts/migrate_metadata.py [--dry-run] [--scan-only]

Options:
    --dry-run     Show what would be done without actually doing it
    --scan-only   Only scan for clips, skip metadata migration
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database import MetadataDB
from app.file_client import FileClient


def scan_clips(file_client: FileClient, db: MetadataDB, dry_run: bool = False) -> dict:
    """Scan storage for all clips and add them to the database."""
    print("\n" + "=" * 60)
    print("Step 1: Scanning for clips")
    print("=" * 60)

    stats = {'added': 0, 'updated': 0, 'failed': 0}

    # List all month directories
    try:
        months = file_client.list_directories("")
    except Exception as e:
        print(f"Error listing directories: {e}")
        return stats

    print(f"Found {len(months)} month(s)\n")

    for month in sorted(months, reverse=True):
        proxy_dir = f"{month}/proxies"
        thumbnails_dir = f"{month}/thumbnails"

        # Get proxy videos
        try:
            proxy_files = file_client.list_files(proxy_dir, pattern="", exclude_proxy=False)
            video_files = [f for f in proxy_files if f.endswith('.mp4')]
        except Exception:
            continue

        if not video_files:
            continue

        # Get thumbnails for this month
        thumbnail_files = set()
        try:
            thumbnail_list = file_client.list_files(thumbnails_dir, pattern="", exclude_proxy=False)
            thumbnail_files = set(f for f in thumbnail_list if f.endswith('.jpg'))
        except Exception:
            pass

        print(f"{month}: {len(video_files)} clips, {len(thumbnail_files)} thumbnails")

        for proxy_filename in video_files:
            # Get display name (strip _proxy suffix)
            display_name = file_client.get_display_name(proxy_filename)
            proxy_path = f"{proxy_dir}/{proxy_filename}"

            # Check if thumbnail exists
            display_stem = Path(display_name).stem
            thumbnail_filename = f"{display_stem}{settings.proxy_suffix}.jpg"
            has_thumbnail = thumbnail_filename in thumbnail_files

            if dry_run:
                status = "NEW" if not db.clip_exists(f"{month}/{display_name}") else "UPDATE"
                print(f"  [{status}] {display_name} (thumb: {has_thumbnail})")
                stats['added'] += 1
            else:
                try:
                    is_new = not db.clip_exists(f"{month}/{display_name}")
                    db.add_clip(month, display_name, proxy_path, has_thumbnail)
                    if is_new:
                        stats['added'] += 1
                    else:
                        stats['updated'] += 1
                except Exception as e:
                    print(f"  ERROR adding {display_name}: {e}")
                    stats['failed'] += 1

    return stats


def migrate_metadata(file_client: FileClient, db: MetadataDB, dry_run: bool = False) -> dict:
    """Migrate metadata from JSON files to SQLite."""
    print("\n" + "=" * 60)
    print("Step 2: Migrating metadata from JSON files")
    print("=" * 60)

    stats = {'migrated': 0, 'failed': 0}

    # List all month directories
    try:
        months = file_client.list_directories("")
    except Exception as e:
        print(f"Error listing directories: {e}")
        return stats

    for month in sorted(months, reverse=True):
        metadata_dir = f"{month}/metadata"

        # Get metadata files
        try:
            files = file_client.list_files(metadata_dir, pattern="", exclude_proxy=False)
            metadata_files = [f for f in files if f.endswith('.metadata.json')]
        except Exception:
            continue

        if not metadata_files:
            continue

        print(f"\n{month}: {len(metadata_files)} metadata file(s)")

        for metadata_file in metadata_files:
            full_path = f"{metadata_dir}/{metadata_file}"

            # Extract clip filename from metadata filename
            # e.g., "video.mp4.metadata.json" -> "video.mp4"
            filename = metadata_file.replace('.metadata.json', '')
            clip_path = f"{month}/{filename}"

            try:
                # Read the JSON metadata
                content = file_client.read_file(full_path)
                metadata = json.loads(content.decode('utf-8'))

                if dry_run:
                    user_meta = metadata.get('metadata', {})
                    fields = list(user_meta.keys()) if user_meta else []
                    print(f"  -> {filename}: {fields}")
                    stats['migrated'] += 1
                else:
                    db.save_metadata(clip_path, metadata)
                    print(f"  -> Migrated: {filename}")
                    stats['migrated'] += 1

            except json.JSONDecodeError as e:
                print(f"  -> ERROR (invalid JSON) {filename}: {e}")
                stats['failed'] += 1
            except Exception as e:
                print(f"  -> ERROR {filename}: {e}")
                stats['failed'] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Scan clips and migrate metadata to SQLite database"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually doing it'
    )
    parser.add_argument(
        '--scan-only',
        action='store_true',
        help='Only scan for clips, skip metadata migration'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Replay Hub: Database Migration")
    print("=" * 60)

    # Initialize file client and database
    file_client = FileClient.create()
    db = MetadataDB()

    print(f"\nStorage backend: {settings.storage_backend}")
    print(f"Database path: {settings.database_path}")

    if args.dry_run:
        print("\n[DRY RUN MODE - No changes will be made]")

    # Step 1: Scan for clips
    clip_stats = scan_clips(file_client, db, dry_run=args.dry_run)

    # Step 2: Migrate metadata (unless --scan-only)
    metadata_stats = {'migrated': 0, 'failed': 0}
    if not args.scan_only:
        metadata_stats = migrate_metadata(file_client, db, dry_run=args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Clips added:      {clip_stats['added']}")
    print(f"Clips updated:    {clip_stats['updated']}")
    print(f"Clips failed:     {clip_stats['failed']}")
    if not args.scan_only:
        print(f"Metadata migrated: {metadata_stats['migrated']}")
        print(f"Metadata failed:   {metadata_stats['failed']}")

    if args.dry_run:
        print("\n[This was a dry run - run without --dry-run to apply changes]")


if __name__ == '__main__':
    main()
