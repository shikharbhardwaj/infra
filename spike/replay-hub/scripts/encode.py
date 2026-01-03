#!/usr/bin/env python3

'''
encode.py -- generate good quality, low bandwidth proxies for clips in the
current folder, using HandbrakeCLI.

Goals:
1. Generate acceptable quality proxies (5mbps 1080p60, h.265).
2. Be resumable.
3. Generate some metadata for each clip (thumbs).

Assumptions:
1. File names don't change.
2. Files are organized in month-chronological order (by arrange.py or
otherwise).
'''

import argparse
import os
import subprocess
import sys
from pathlib import Path


def get_month_folders(directory):
    """Find all month-formatted folders (YYYY-MM) in the directory."""
    path = Path(directory)
    month_folders = []

    for item in path.iterdir():
        if item.is_dir():
            # Check if folder name matches YYYY-MM pattern
            name = item.name
            if len(name) == 7 and name[4] == '-':
                try:
                    year = int(name[:4])
                    month = int(name[5:7])
                    if 1 <= month <= 12:
                        month_folders.append(item)
                except ValueError:
                    continue

    return sorted(month_folders)


def get_video_files(directory, extensions=('.mp4', '.mkv', '.mov', '.avi', '.webm')):
    """Find all video files in the directory (non-recursive)."""
    video_files = []
    path = Path(directory)
    for ext in extensions:
        video_files.extend(path.glob(f'*{ext}'))
    return sorted(video_files)


def get_output_path(input_path, suffix='_proxy'):
    """Generate output path for the encoded file in a proxies subfolder."""
    stem = input_path.stem
    output_filename = f"{stem}{suffix}.mp4"
    proxies_dir = input_path.parent / 'proxies'
    proxies_dir.mkdir(exist_ok=True)
    return proxies_dir / output_filename


def encode_video(input_path, output_path, bitrate='5000', resolution='1920:1080', framerate='60'):
    """
    Encode video using HandBrakeCLI with NVENC hardware acceleration.

    Args:
        input_path: Path to input video file
        output_path: Path to output video file
        bitrate: Target video bitrate in kbps (default: 5000)
        resolution: Output resolution as width:height (default: 1920:1080)
        framerate: Target framerate (default: 60)
    """
    # Create temporary output path in .cache subfolder
    cache_dir = input_path.parent / '.cache'
    cache_dir.mkdir(exist_ok=True)
    temp_output = cache_dir / f"{output_path.stem}_temp{output_path.suffix}"

    cmd = [
        'HandBrakeCLI',
        '-i', str(input_path),
        '-o', str(temp_output),  # Encode to temp location first
        '--encoder', 'nvenc_h265',  # NVENC H.265 hardware encoder
        '--encoder-preset', 'medium',  # Quality preset
        '--vb', bitrate,  # Video bitrate
        '--width', resolution.split(':')[0],  # Video width
        '--height', resolution.split(':')[1],  # Video height
        '--rate', framerate,  # Framerate
        '--cfr',  # Constant framerate
        '--all-audio',  # Copy all audio tracks
        '--aencoder', 'copy',  # Copy audio without re-encoding
        '--format', 'av_mp4',  # Output format
    ]

    print(f"Encoding: {input_path.name}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=False)

        if result.returncode == 0:
            # Only move to final location if encoding succeeded
            import shutil
            shutil.move(str(temp_output), str(output_path))
            print(f"✓ Successfully encoded: {output_path.name}\n")
            return True
        else:
            print(f"✗ HandBrakeCLI failed with exit code {result.returncode}: {input_path.name}\n", file=sys.stderr)
            # Clean up partial output file if it exists
            if temp_output.exists():
                temp_output.unlink()
            return False
    except FileNotFoundError:
        print("Error: HandBrakeCLI not found. Please install HandBrake CLI.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        # Clean up temp file on interrupt
        print(f"\n\n⚠ Interrupted! Cleaning up temporary file...\n", file=sys.stderr)
        if temp_output.exists():
            temp_output.unlink()
        raise


def process_folder(folder_path, args):
    """Process all video files in a single folder."""
    video_files = get_video_files(folder_path)

    if not video_files:
        return 0, 0, 0

    print(f"\n{'='*60}")
    print(f"Processing folder: {folder_path.name}")
    print(f"{'='*60}")
    print(f"Found {len(video_files)} video file(s)\n")

    encoded_count = 0
    skipped_count = 0
    failed_count = 0

    for video_file in video_files:
        output_path = get_output_path(video_file, args.suffix)

        # Skip if already encoded (resumable)
        if output_path.exists() and not args.force:
            print(f"⊘ Skipping (already exists): {video_file.name}")
            skipped_count += 1
            continue

        success = encode_video(
            video_file,
            output_path,
            args.bitrate,
            args.resolution,
            args.framerate
        )

        if success:
            encoded_count += 1
        else:
            failed_count += 1

    return encoded_count, skipped_count, failed_count


def main():
    parser = argparse.ArgumentParser(
        description='Generate quality proxies for video clips using HandBrakeCLI with NVENC acceleration.'
    )
    parser.add_argument(
        'input_dir',
        nargs='?',
        default='.',
        help='Root directory containing month folders (YYYY-MM format) with video files'
    )
    parser.add_argument(
        '-b', '--bitrate',
        default='5000',
        help='Video bitrate in kbps (default: 5000)'
    )
    parser.add_argument(
        '-r', '--resolution',
        default='1920:1080',
        help='Output resolution as width:height (default: 1920:1080)'
    )
    parser.add_argument(
        '-f', '--framerate',
        default='60',
        help='Target framerate (default: 60)'
    )
    parser.add_argument(
        '--suffix',
        default='_proxy',
        help='Suffix for output filenames (default: _proxy)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Re-encode files even if output already exists'
    )

    args = parser.parse_args()

    # Find all month folders
    month_folders = get_month_folders(args.input_dir)

    if not month_folders:
        print(f"No month folders (YYYY-MM format) found in {args.input_dir}")
        print("Expected folder structure: 2024-01, 2024-02, etc.")
        return

    print(f"Found {len(month_folders)} month folder(s): {', '.join(f.name for f in month_folders)}")

    # Process each month folder
    total_encoded = 0
    total_skipped = 0
    total_failed = 0

    for month_folder in month_folders:
        encoded, skipped, failed = process_folder(month_folder, args)
        total_encoded += encoded
        total_skipped += skipped
        total_failed += failed

    # Print overall summary
    print("\n" + "="*60)
    print("OVERALL SUMMARY")
    print("="*60)
    print(f"Month folders processed: {len(month_folders)}")
    print(f"Successfully encoded: {total_encoded}")
    print(f"Skipped (already exist): {total_skipped}")
    print(f"Failed: {total_failed}")


if __name__ == '__main__':
    main()
