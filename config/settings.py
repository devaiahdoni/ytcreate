import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General Configuration
    PROJECT_NAME: str = "ytcreate"
    DEBUG: bool = False
    OUTPUT_DIR: str = str(Path("C:/git/python/ytcreate/output"))

    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ytcreate"

    # Redis and Celery Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # API Keys & Credentials
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    FLOW_API_KEY: Optional[str] = None
    FLOW_API_URL: str = "https://flow.googleapis.com/v1"
    ELEVENLABS_API_KEY: Optional[str] = None

    # YouTube Data API Configuration
    YOUTUBE_CLIENT_ID: Optional[str] = None
    YOUTUBE_CLIENT_SECRET: Optional[str] = None
    YOUTUBE_REFRESH_TOKEN: Optional[str] = None
    YOUTUBE_REDIRECT_URI: str = "http://localhost:8080/oauth2callback"

    @property
    def output_path(self) -> Path:
        path = Path(self.OUTPUT_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

settings = Settings()
