"""Configuration management for Replay Hub."""

import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Storage Backend Configuration
    storage_backend: Literal["webdav", "local"] = "webdav"

    # WebDAV Configuration (used when storage_backend="webdav")
    webdav_url: str = ""
    webdav_username: str = ""
    webdav_password: str = ""
    webdav_root_path: str = "replays/"

    # Local Filesystem Configuration (used when storage_backend="local")
    local_root_path: str = "~/replay-hub-storage"

    # Application Configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8080
    log_level: str = "INFO"

    # Optional Configuration
    clips_per_page: int = 24
    use_proxy_videos: bool = True
    proxy_suffix: str = "_proxy"


# Global settings instance
settings = Settings()
