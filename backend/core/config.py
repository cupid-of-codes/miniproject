"""Configuration settings for VibeVerse AI."""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="VibeVerse AI", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # MySQL Database
    mysql_host: str = Field(default="localhost", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_database: str = Field(default="vibeverse_ai", alias="MYSQL_DATABASE")
    mysql_user: str = Field(default="root", alias="MYSQL_USER")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")
    database_url_override: Optional[str] = Field(default=None, alias="DATABASE_URL")

    # FastAPI
    fastapi_host: str = Field(default="127.0.0.1", alias="FASTAPI_HOST")
    fastapi_port: int = Field(default=8000, alias="FASTAPI_PORT")
    api_base_url: str = Field(default="http://127.0.0.1:8000", alias="API_BASE_URL")

    # Data & External APIs
    data_mode: str = Field(default="auto", alias="DATA_MODE")
    tmdb_api_key: str = Field(default="", alias="TMDB_API_KEY")
    tmdb_base_url: str = Field(default="https://api.themoviedb.org/3", alias="TMDB_BASE_URL")
    tmdb_image_base_url: str = Field(
        default="https://image.tmdb.org/t/p/w500", alias="TMDB_IMAGE_BASE_URL"
    )
    musicbrainz_base_url: str = Field(
        default="https://musicbrainz.org/ws/2", alias="MUSICBRAINZ_BASE_URL"
    )
    musicbrainz_user_agent: str = Field(
        default="VibeVerseAI/1.0 (https://localhost)", alias="MUSICBRAINZ_USER_AGENT"
    )

    # Paths & Cache
    raw_data_dir: str = Field(default="data/raw", alias="RAW_DATA_DIR")
    processed_data_dir: str = Field(default="data/processed", alias="PROCESSED_DATA_DIR")
    cache_dir: str = Field(default="data/cache", alias="CACHE_DIR")
    cache_ttl_hours: int = Field(default=72, alias="CACHE_TTL_HOURS")

    @property
    def sqlalchemy_database_url(self) -> str:
        """Build SQLAlchemy MySQL+PyMySQL connection URI."""
        if self.database_url_override:
            return self.database_url_override
        encoded_user = quote_plus(self.mysql_user)
        encoded_password = quote_plus(self.mysql_password)
        return (
            f"mysql+pymysql://{encoded_user}:{encoded_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def mysql_server_url(self) -> str:
        """Build SQLAlchemy MySQL server URI without database name (for DB creation)."""
        encoded_user = quote_plus(self.mysql_user)
        encoded_password = quote_plus(self.mysql_password)
        return (
            f"mysql+pymysql://{encoded_user}:{encoded_password}"
            f"@{self.mysql_host}:{self.mysql_port}/?charset=utf8mb4"
        )

    def resolve_path(self, relative_or_abs: str) -> Path:
        """Resolve a project path cleanly."""
        path = Path(relative_or_abs)
        return path if path.is_absolute() else PROJECT_ROOT / path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
