"""
Konfigurasi terpusat untuk Thesa Python API.

Semua nilai dibaca dari environment variables (atau file .env).
Menggunakan pydantic-settings agar type-safe dan mudah di-override di berbagai environment.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Setting utama aplikasi.
    Urutan prioritas: environment variable → .env file → default value.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --------------------------------------------------------------------------
    # API & Server
    # --------------------------------------------------------------------------
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_allowed_origins: List[str] = ["*"]

    # --------------------------------------------------------------------------
    # Redis
    # --------------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # --------------------------------------------------------------------------
    # Celery (menggunakan Redis sebagai broker dan backend)
    # --------------------------------------------------------------------------
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # --------------------------------------------------------------------------
    # Job Configuration
    # --------------------------------------------------------------------------
    job_ttl_seconds: int = 3600           # Berapa lama hasil job disimpan di Redis
    sse_keepalive_seconds: int = 15       # Interval kirim SSE keepalive ping

    # --------------------------------------------------------------------------
    # NeoMakalah Engine
    # --------------------------------------------------------------------------
    openrouter_api_key: str = ""
    openrouter_api_url: str = "https://openrouter.ai/api/v1/chat/completions"
    cloudmersive_api_key: str = ""

    # --------------------------------------------------------------------------
    # Output storage
    # --------------------------------------------------------------------------
    output_dir: str = "output"            # Relatif dari root Backend


@lru_cache()
def get_settings() -> Settings:
    """
    Mengembalikan singleton Settings.
    Gunakan ini via dependency injection FastAPI agar testable.
    """
    return Settings()


# Shortcut untuk import langsung
settings = get_settings()
