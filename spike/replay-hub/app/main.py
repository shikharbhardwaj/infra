"""Main FastAPI application for Replay Hub."""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.routes import clips, metadata

# Configure logging (matching existing spike project format)
logging.basicConfig(
    level=settings.log_level,
    format='[%(levelname)8s] %(asctime)s %(filename)16s:L%(lineno)-3d %(funcName)16s() : %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Replay Hub application")
    logger.info(f"WebDAV URL: {settings.webdav_url}")
    logger.info(f"WebDAV root path: {settings.webdav_root_path}")
    yield
    # Shutdown
    logger.info("Shutting down Replay Hub application")


# Create FastAPI app
app = FastAPI(
    title="Replay Hub",
    description="Shadowplay Clip Annotation Tool",
    version="0.1.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="app/templates")

# Register routes
app.include_router(clips.router)
app.include_router(metadata.router)


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker."""
    return {"status": "healthy", "version": "0.1.0"}
