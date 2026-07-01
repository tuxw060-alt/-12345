"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from .env file and environment variables."""

    # DeepSeek API
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL"
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/accounts.db", alias="DATABASE_URL"
    )

    # Auth
    app_password: str = Field(default="admin123", alias="APP_PASSWORD")
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")

    # App
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    # File paths
    upload_dir: str = Field(default="./data/uploads", alias="UPLOAD_DIR")
    export_dir: str = Field(default="./data/exports", alias="EXPORT_DIR")

    # Derived paths
    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def export_path(self) -> Path:
        p = Path(self.export_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def data_path(self) -> Path:
        p = Path("./data")
        p.mkdir(parents=True, exist_ok=True)
        return p

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
