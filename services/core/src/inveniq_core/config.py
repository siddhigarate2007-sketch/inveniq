from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration settings for InvenIQ."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "InvenIQ"
    APP_PORT: int = 8000
    SECRET_KEY: str = "tbo-inveniq-super-secure-production-ready-jwt-secret-key-32chars"

    # Database & Cache
    DATABASE_URL: str = "postgresql+asyncpg://inveniq_user:inveniq_secure_pass@localhost:5432/inveniq_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Object Storage / Lakehouse
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_BUCKET_NAME: str = "inveniq-artifacts"
    LAKEHOUSE_PATH: str = str(Path(__file__).resolve().parents[4] / "data" / "lakehouse")
    RAW_DATA_PATH: str = str(Path(__file__).resolve().parents[4] / "data" / "raw")

    # Optimization Defaults
    DEFAULT_BUDGET_INR: float = 50_000_000.0  # 5 Crore INR
    DEFAULT_RISK_APPETITE: str = "BALANCED"
    DEFAULT_CVAR_ALPHA: float = 0.95
    MAX_SOLVER_TIME_SECONDS: int = 60


settings = Settings()
