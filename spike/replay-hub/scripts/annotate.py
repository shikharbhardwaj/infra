#!/usr/bin/env python3
"""
annotate.py -- Use a multimodal LLM to annotate a gameplay clip with metadata.

Extracts frames from the video, sends them to LM Studio (OpenAI-compatible API),
and outputs metadata in the replay-hub format (map, rating, description, clip_type).

Usage:
    python scripts/annotate.py <video_file> [options]
"""

import argparse
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: uv add openai", file=sys.stderr)
    sys.exit(1)


DEFAULT_API_URL = "http://100.100.176.44:1234/v1"

CLIP_TYPES = ['Clutch', 'Highlight', 'Funny', 'Fail', 'Tutorial', 'Gameplay', 'Other']

SYSTEM_PROMPT = """You are an expert FPS/competitive gameplay clip analyst. You will be shown frames sampled from the last 30 seconds of a gameplay clip.

Analyze the frames carefully and produce structured metadata:

- map: The map or game level name (e.g. "Dust 2", "Erangel", "Hanamura"). Use null if unidentifiable.

- rating: Integer 1-5 excitement/quality rating.
  1 = routine/boring play, 3 = solid play, 5 = exceptional or highlight-worthy.

- description: 1-2 sentence factual description of what happens (kills, positioning, outcome).

- clip_type: Exactly one of: Clutch, Highlight, Funny, Fail, Tutorial, Gameplay, Other.
  Use "Clutch" when the player wins a round or fight against multiple opponents while at a disadvantage
  (e.g. 1vN situations, low health, outnumbered). Look for: multiple elimination feed entries in
  sequence, low HP indicators, round-win notifications, ace/clutch medals or callouts on screen.
  Use "Highlight" for exceptional individual plays that are not clutch situations.
  Default to "Gameplay" only for ordinary, unremarkable footage.

- kill_count: Integer number of kills/eliminations visible in this clip. Count kill feed entries,
  elimination popups, or score increments. Use 0 if none are visible, null if impossible to determine.

Respond ONLY with a valid JSON object, no markdown fences or extra text:
{"map": "...", "rating": 3, "description": "...", "clip_type": "Gameplay", "kill_count": 0}"""


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_format', str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    info = json.loads(result.stdout)
    return float(info['format']['duration'])


SAMPLE_WINDOW = 30   # seconds from end of clip to sample
SAMPLE_FPS = 1       # frames per second within that window


def extract_frames(video_path: Path, keep_frames_dir: Path | None = None) -> list[bytes]:
    """Extract 1 frame per second from the last 30 seconds of the clip.

    If keep_frames_dir is provided, frames are saved there and kept after
    the function returns (useful for debugging). Otherwise a temporary
    directory is used and cleaned up automatically.
    """
    duration = get_video_duration(video_path)
    start = max(0.0, duration - SAMPLE_WINDOW)
    window = duration - start

    print(f"  clip duration: {duration:.1f}s  |  sampling last {window:.1f}s at {SAMPLE_FPS}fps", file=sys.stderr)

    def _extract_to(workdir: str) -> list[bytes]:
        cmd = [
            'ffmpeg',
            '-ss', str(start),
            '-i', str(video_path),
            '-vf', f'fps={SAMPLE_FPS},scale=1280:-1',
            '-q:v', '3',                              # JPEG quality (1-31, lower=better)
            '-y', f'{workdir}/frame_%03d.jpg'
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg frame extraction failed: {result.stderr.decode()}")

        paths = sorted(Path(workdir).glob('frame_*.jpg'))
        frames = []
        for p in paths:
            # Rename to include timestamp for easier inspection
            offset = start + (int(p.stem.split('_')[1]) - 1) / SAMPLE_FPS
            dest = p.parent / f"frame_{p.stem.split('_')[1]}_t{offset:.1f}s.jpg"
            p.rename(dest)
            with open(dest, 'rb') as f:
                frames.append(f.read())
        return frames

    if keep_frames_dir is not None:
        keep_frames_dir.mkdir(parents=True, exist_ok=True)
        frames = _extract_to(str(keep_frames_dir))
        print(f"Frames saved to: {keep_frames_dir}", file=sys.stderr)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            frames = _extract_to(tmpdir)

    if not frames:
        raise RuntimeError("Failed to extract any frames from the video")

    return frames


def build_content(frames: list[bytes]) -> list[dict]:
    """Build the multimodal message content from frame bytes."""
    content: list[dict] = [
        {"type": "text", "text": "Analyze these frames from a gameplay clip and provide the metadata JSON."}
    ]
    for frame_bytes in frames:
        b64 = base64.b64encode(frame_bytes).decode('utf-8')
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })
    return content


def parse_metadata(raw: str) -> dict:
    """Parse and validate metadata from the LLM response."""
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split('\n')
        text = '\n'.join(lines[1:-1]).strip()

    data = json.loads(text)

    result = {}

    if data.get('map') and data['map'] != 'null':
        result['map'] = str(data['map'])

    rating = data.get('rating')
    if rating is not None:
        try:
            result['rating'] = max(1, min(5, int(rating)))
        except (ValueError, TypeError):
            pass

    if data.get('description'):
        result['description'] = str(data['description'])

    clip_type = data.get('clip_type', '')
    for ct in CLIP_TYPES:
        if ct.lower() == str(clip_type).lower():
            result['clip_type'] = ct
            break

    kill_count = data.get('kill_count')
    if kill_count is not None:
        try:
            result['kill_count'] = int(kill_count)
        except (ValueError, TypeError):
            pass

    return result


def resolve_model(client: OpenAI) -> str:
    """Pick the first available model from LM Studio."""
    models = client.models.list()
    ids = [m.id for m in models.data]
    if not ids:
        raise RuntimeError("No models available in LM Studio")
    return ids[0]


def annotate_clip(video_path: Path, api_url: str, model: str | None, keep_frames_dir: Path | None = None) -> dict:
    """Full pipeline: extract frames → call LLM → return parsed metadata."""
    client = OpenAI(api_key="lm-studio", base_url=api_url)

    if model is None:
        model = resolve_model(client)
        print(f"Using model: {model}", file=sys.stderr)

    print(f"Extracting frames from {video_path.name}...", file=sys.stderr)
    frames = extract_frames(video_path, keep_frames_dir)
    print(f"Extracted {len(frames)} frame(s). Sending to LLM...", file=sys.stderr)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_content(frames)},
        ],
        temperature=0.1,
        max_tokens=512,
    )

    raw = response.choices[0].message.content or ""
    return parse_metadata(raw)


def main():
    parser = argparse.ArgumentParser(
        description='Annotate a gameplay clip with LLM-generated metadata.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/annotate.py clip.mp4
  python scripts/annotate.py clip.mp4 --model gemma3-27b
  python scripts/annotate.py clip.mp4 --keep-frames /tmp/frames --output json
        """
    )
    parser.add_argument('video', help='Path to the gameplay clip (mp4, mkv, etc.)')
    parser.add_argument(
        '--api-url',
        default=DEFAULT_API_URL,
        help=f'LM Studio API base URL (default: {DEFAULT_API_URL})'
    )
    parser.add_argument(
        '--model',
        default=None,
        help='Model ID to use (default: first available model in LM Studio)'
    )
    parser.add_argument(
        '--output',
        choices=['json', 'pretty'],
        default='pretty',
        help='Output format: pretty (human-readable) or json (machine-readable, default: pretty)'
    )
    parser.add_argument(
        '--keep-frames',
        metavar='DIR',
        default=None,
        help='Save extracted frames to DIR for inspection instead of deleting them'
    )

    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    keep_frames_dir = Path(args.keep_frames) if args.keep_frames else None

    try:
        metadata = annotate_clip(video_path, args.api_url, args.model, keep_frames_dir)
    except json.JSONDecodeError as e:
        print(f"Error: could not parse LLM response as JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output == 'json':
        print(json.dumps(metadata))
    else:
        stars = '★' * metadata.get('rating', 0) + '☆' * (5 - metadata.get('rating', 0))
        print()
        print(f"  map:         {metadata.get('map', '(unidentified)')}")
        print(f"  rating:      {stars}  ({metadata.get('rating', 'N/A')}/5)")
        print(f"  clip_type:   {metadata.get('clip_type', '(unidentified)')}")
        print(f"  kill_count:  {metadata.get('kill_count', '(unknown)')}")
        print(f"  description: {metadata.get('description', '(none)')}")
        print()
        print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
