# Replay Hub

A web application for annotating Shadowplay instant replay clips stored in Nextcloud/WebDAV storage.

## Features

- 📁 **Browse clips** organized by month from WebDAV storage
- 🎥 **Video playback** with web-optimized proxy support
- 📝 **Free-form metadata** annotation with key-value pairs
- 🔍 **Real-time search** and filtering
- 🎨 **Clean, responsive UI** with TailwindCSS
- 🐳 **Docker deployment** for easy self-hosting
- ⌨️ **Keyboard shortcuts** for efficient navigation

## Technology Stack

- **Backend**: FastAPI (Python 3.10+)
- **Frontend**: Jinja2 templates + TailwindCSS (CDN) + HTMX
- **Storage**: WebDAV (Nextcloud)
- **Deployment**: Docker + docker-compose

## Prerequisites

- Python 3.10 or higher
- Access to a Nextcloud instance with WebDAV
- Docker (for containerized deployment)
- `uv` package manager (recommended for development)

## Installation

### Option 1: Local Development with uv

1. **Clone the repository**
   ```bash
   cd spike/replay-hub
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your WebDAV credentials
   ```

4. **Run the application**
   ```bash
   uv run uvicorn app.main:app --reload --port 8080
   ```

5. **Access the application**
   ```
   http://localhost:8080
   ```

### Option 2: Docker Deployment

1. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your WebDAV credentials
   ```

2. **Build and run with docker-compose**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   ```
   http://localhost:8080
   ```

4. **View logs**
   ```bash
   docker-compose logs -f
   ```

5. **Stop the application**
   ```bash
   docker-compose down
   ```

### Option 3: Docker Build Only

```bash
docker build -t replay-hub .
docker run -d \
  -p 8080:8080 \
  -e WEBDAV_URL=https://nextcloud.example.com/remote.php/dav/files/username/ \
  -e WEBDAV_USERNAME=user \
  -e WEBDAV_PASSWORD=pass \
  -e WEBDAV_ROOT_PATH=replays/ \
  --name replay-hub \
  replay-hub
```

## Configuration

Configure the application via environment variables in `.env`:

### Required Settings

| Variable | Description | Example |
|----------|-------------|---------|
| `WEBDAV_URL` | WebDAV endpoint URL | `https://nextcloud.example.com/remote.php/dav/files/username/` |
| `WEBDAV_USERNAME` | WebDAV username | `myuser` |
| `WEBDAV_PASSWORD` | WebDAV password | `mypassword` |
| `WEBDAV_ROOT_PATH` | Root path for clips | `replays/` |

### Optional Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_HOST` | Server bind address | `0.0.0.0` |
| `APP_PORT` | Server port | `8080` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CLIPS_PER_PAGE` | Pagination limit | `24` |
| `USE_PROXY_VIDEOS` | Prefer proxy videos | `true` |
| `PROXY_SUFFIX` | Proxy filename suffix | `_proxy` |

## WebDAV Storage Structure

Organize your clips in WebDAV storage with the following structure:

```
shadowplay/
├── 2024-11/
│   ├── proxies/                                                    # Web-optimized videos
│   │   ├── Counter-strike 2 2024.11.15 - 12.45.23_proxy.mp4
│   │   └── Counter-strike 2 2024.11.18 - 18.32.11_proxy.mp4
│   └── metadata/                                                   # Metadata files
│       ├── Counter-strike 2 2024.11.15 - 12.45.23.mp4.metadata.json
│       └── Counter-strike 2 2024.11.18 - 18.32.11.mp4.metadata.json
├── 2024-12/
│   ├── proxies/
│   └── metadata/
└── 2025-01/
    ├── proxies/
    └── metadata/
```

**Key Points:**
- **Proxy videos** are stored in `{month}/proxies/` with `_proxy` suffix (e.g., `clip_proxy.mp4`)
- **Metadata** is stored in `{month}/metadata/` without the `_proxy` suffix (e.g., `clip.mp4.metadata.json`)
- The UI automatically hides the `_proxy` suffix for cleaner display
- Proxies are used for streaming, but displayed as original filenames

### Optional: Original High-Quality Videos

You can optionally keep original videos in the month directory root:

```
shadowplay/
├── 2024-11/
│   ├── Counter-strike 2 2024.11.15 - 12.45.23.mp4       # Original (optional)
│   ├── proxies/
│   │   └── Counter-strike 2 2024.11.15 - 12.45.23_proxy.mp4
│   └── metadata/
│       └── Counter-strike 2 2024.11.15 - 12.45.23.mp4.metadata.json
```

The application only uses files from the `proxies/` folder for streaming.

## Metadata Format

Metadata is stored as JSON files alongside video clips:

```json
{
  "version": "1.0",
  "created_at": "2025-01-03T20:30:00Z",
  "updated_at": "2025-01-03T20:35:00Z",
  "metadata": {
    "game": "Counter-Strike 2",
    "map": "de_ancient",
    "description": "Insane AWP 4K clutch",
    "clip_type": "highlight",
    "rating": "5",
    "tags": "cs2, awp, clutch"
  }
}
```

Fields are completely free-form - add any key-value pairs you need!

## Usage

### Browsing Clips

1. Navigate to the homepage to see all clips grouped by month
2. Use the search box to filter clips (press `/` to focus)
3. Click on a clip card to view details

### Annotating Clips

1. Open a clip detail page
2. Add metadata fields using the "Add Field" button
3. Enter field names and values
4. Click "Save Metadata" to store
5. Remove fields by clicking the ✕ button

### Keyboard Shortcuts

**Homepage:**
- `/` - Focus search box
- `Esc` - Clear search

**Video Player:**
- `Space` - Play/Pause
- `←` / `→` - Skip backward/forward 5 seconds
- `f` - Fullscreen
- `m` - Mute/Unmute

## Development

### Project Structure

```
spike/replay-hub/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic models
│   ├── webdav_client.py     # WebDAV operations
│   ├── routes/
│   │   ├── clips.py         # Clip browsing & viewing
│   │   └── metadata.py      # Metadata CRUD
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS & JavaScript
├── scripts/                 # Utility scripts
├── tests/                   # Test files
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml           # Python dependencies
└── README.md
```

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black app/
```

### Type Checking

```bash
uv run mypy app/
```

## Utility Scripts

The `scripts/` directory contains helper tools:

- **`migrate_metadata.py`** - Migrate metadata from old structure (proxies folder) to new structure (metadata folder)
  ```bash
  # Dry run (see what would be migrated)
  uv run python scripts/migrate_metadata.py

  # Actually perform migration
  uv run python scripts/migrate_metadata.py --apply
  ```
- `arrange.py` - Organize clips by month (to be integrated)
- `encode.py` - Generate proxy videos (to be integrated)

## Troubleshooting

### Connection Issues

If you can't connect to WebDAV:

1. Verify `WEBDAV_URL` is correct (should end with `/`)
2. Check username and password
3. Ensure WebDAV is enabled in Nextcloud
4. Test connection manually:
   ```bash
   curl -u username:password https://nextcloud.example.com/remote.php/dav/files/username/
   ```

### No Clips Showing

1. Verify clips are in the correct directory structure (month folders)
2. Check `WEBDAV_ROOT_PATH` setting
3. Check application logs for errors

### Video Won't Play

1. Ensure video is in MP4 format
2. Check browser console for errors
3. Try creating a proxy video for web streaming

### Metadata Not Saving

1. Check WebDAV write permissions
2. Look for errors in application logs
3. Verify JSON format in metadata files

## Contributing

This is a personal project in the spike directory, but suggestions are welcome!

## License

Personal use project - no formal license.

## Acknowledgments

- Built with FastAPI, TailwindCSS, and HTMX
- WebDAV integration via webdavclient3
- Designed for Shadowplay instant replay management
