"""Application configuration settings."""
from pathlib import Path
from typing import List, Optional, Any, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables."""
    APP_NAME: str = "T.R.A.C.E."
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ]

    # Media and upload limits
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_IMAGE_EXTENSIONS: Union[List[str], str] = [".jpg", ".jpeg", ".png", ".webp"]
    TEMP_UPLOAD_DIR: str = "temp_uploads"

    @field_validator("CORS_ORIGINS", "ALLOWED_IMAGE_EXTENSIONS")
    @classmethod
    def normalize_list(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                import json
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [item.strip() for item in v_str.split(",") if item.strip()]
        return v

    # AI Model & Azure AI Foundry Settings
    MODEL_ID: str = "azure-vision-detector"
    MODEL_DEVICE: str = "cloud"
    
    AZURE_AI_ENDPOINT: Optional[str] = None
    AZURE_AI_API_KEY: Optional[str] = None
    AZURE_AI_DEPLOYMENT_NAME: Optional[str] = None
    AZURE_AI_API_VERSION: str = "2024-08-01-preview"
    AZURE_AI_REQUEST_TIMEOUT_SECONDS: float = 30.0
    AZURE_AI_MAX_RETRIES: int = 1

    # Feature Toggles
    ENABLE_PROVENANCE_CHECK: bool = False
    OFFICIAL_REPORTING_URL: str = "https://cybercrime.gov.in/"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", str(Path(__file__).resolve().parent.parent / ".env")),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
