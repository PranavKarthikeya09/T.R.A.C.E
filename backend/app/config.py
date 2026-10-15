"""Application configuration settings."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables."""
    APP_NAME: str = "T.R.A.C.E."
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ]

    # Media and upload limits
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]
    TEMP_UPLOAD_DIR: str = "temp_uploads"

    # AI Model Settings
    MODEL_ID: str = "candidate-detector-v1"
    MODEL_DEVICE: str = "cpu"

    # Feature Toggles
    ENABLE_PROVENANCE_CHECK: bool = False
    OFFICIAL_REPORTING_URL: str = "https://cybercrime.gov.in/"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
