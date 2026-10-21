"""Application configuration using environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings  # type: ignore[import-untyped]


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:9092", description="Kafka broker list")
    KAFKA_ENABLED: bool = Field(default=False, description="Enable Kafka event publishing")
    MODEL_PATH: str = Field(default="models/fraud_model.onnx", description="ONNX model path")
    XGBOOST_MODEL_PATH: str = Field(default="models/fraud_model.pkl", description="XGBoost model path")
    LOG_LEVEL: str = Field(default="INFO", description="Python logging level")
    APP_ENV: str = Field(default="development", description="Application environment")
    LLM_API_KEY: str = Field(default="", description="Optional LLM API key for AI investigator")
    API_KEY: str = Field(default="", description="Require X-API-Key header on mutating endpoints when set; empty disables")
    BACKEND_ORIGINS: str = Field(
        default="http://localhost:5173,http://localhost:3000,http://localhost:8501",
        description="Comma-separated explicit CORS allowlist",
    )
    LLM_MODEL: str = Field(default="gpt-4o-mini", description="LLM model name")
    MODEL_FEATURES: list[str] = Field(
        default=[
            "amount",
            "account_velocity_1h",
            "amount_sum_24h",
            "speed_kmh",
            "is_new_device",
        ]
    )

    # Suspicious entities for graph analysis
    SUSPICIOUS_DEVICES: list[str] = Field(
        default=["device_suspicious_01", "device_suspicious_02"]
    )
    SUSPICIOUS_IPS: list[str] = Field(
        default=["10.10.10.10", "192.168.1.100"]
    )
    SUSPICIOUS_USERS: list[str] = Field(
        default=["user_flagged_01"]
    )

    # Decision thresholds
    ML_RISK_THRESHOLD: float = Field(default=0.85, description="ML risk score threshold for investigation")
    GRAPH_PENALTY_THRESHOLD: float = Field(default=70.0, description="Graph penalty threshold for investigation")
    IMPOSSIBLE_TRAVEL_SPEED: float = Field(default=800.0, description="Speed in km/h for impossible travel")

    # Auth / identity risk thresholds (Predictive Cybersecurity Intelligence)
    AUTH_MAX_SPEED: float = Field(default=900.0, description="Speed in km/h beyond which travel is impossible")
    AUTH_STEP_UP_THRESHOLD: float = Field(default=40.0, description="Risk score requiring step-up auth (MFA)")
    AUTH_BLOCK_THRESHOLD: float = Field(default=80.0, description="Risk score blocking the session")

    # Redis TTLs (seconds)
    TRANSACTION_HISTORY_TTL: int = Field(default=86400, description="TTL for transaction records (24h)")
    LOCATION_TTL: int = Field(default=604800, description="TTL for location records (7 days)")
    DEVICE_TTL: int = Field(default=2592000, description="TTL for device records (30 days)")

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent


settings = Settings()
