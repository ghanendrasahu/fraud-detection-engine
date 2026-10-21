"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader

from app.config import settings
from app.kafka_producer import kafka_producer
from app.logging_config import get_logger, setup_logging
from app.schemas import (
    AuthAssessment,
    AuthEvent,
    HealthResponse,
    ModelInfoResponse,
    TransactionEvent,
    TransactionResponse,
)
from app.services.fraud_service import FraudService

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(x_api_key: str | None = Security(_api_key_header)) -> None:
    """Gate mutating endpoints when ``API_KEY`` is configured (off when empty)."""
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")


def _cors_origins() -> list[str]:
    """Explicit allowlist: browsers reject `["*"]` together with credentials."""
    return [origin.strip() for origin in settings.BACKEND_ORIGINS.split(",") if origin.strip()]

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

fraud_service: FraudService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global fraud_service
    setup_logging()
    logger.info("Starting fraud-detection-engine (env=%s)", settings.APP_ENV)
    fraud_service = FraudService()
    logger.info("FraudService initialized")
    yield
    kafka_producer.close()
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Fraud Detection Engine",
    description="Real-time transaction fraud detection with ML, graph intelligence, and explainable decisions.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    if fraud_service is None:
        return HealthResponse(status="starting", redis="unknown", model="unknown", graph="unknown")
    status = fraud_service.health_check()
    return HealthResponse(
        status="healthy",
        redis=status.get("redis", "unknown"),
        model=status.get("model", "unknown"),
        graph=status.get("graph", "unknown"),
    )


@app.post("/v1/transactions", response_model=TransactionResponse, dependencies=[Depends(require_api_key)])
async def process_transaction(event: TransactionEvent) -> TransactionResponse:
    if fraud_service is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        result = fraud_service.process_transaction(event)
    except Exception as e:
        logger.error("Transaction processing failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal processing error")

    # Publish to Kafka (non-blocking)
    try:
        kafka_producer.publish_transaction_event(event.model_dump(mode="json"))
        kafka_producer.publish_fraud_decision(result.model_dump(mode="json"))
    except Exception:
        pass

    return result


@app.get("/v1/transactions/{transaction_id}")
async def get_transaction(transaction_id: str) -> dict:
    if fraud_service is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    # Stub: in production, query from database
    raise HTTPException(status_code=404, detail="Transaction not found in store")


@app.get("/v1/model/info", response_model=ModelInfoResponse)
async def model_info() -> ModelInfoResponse:
    if fraud_service is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return ModelInfoResponse(
        model_type="XGBoost / ONNX",
        features=settings.MODEL_FEATURES,
        threshold=settings.ML_RISK_THRESHOLD,
        onnx_available=fraud_service.ml_engine._onnx_available,
    )


# ---------------------------------------------------------------------------
# Predictive Cybersecurity Intelligence - identity / auth anomaly scoring
# ---------------------------------------------------------------------------

@app.post("/v1/auth-events", response_model=AuthAssessment, dependencies=[Depends(require_api_key)])
async def score_auth_event(event: AuthEvent) -> AuthAssessment:
    """Score a login/identity event against the user's behavioural baseline."""
    from app.auth_guard import get_auth_guard

    try:
        return get_auth_guard().assess(event)
    except Exception:
        logger.exception("Auth event scoring failed")
        raise HTTPException(status_code=500, detail="Internal auth scoring error")


@app.get("/v1/auth-events/{user_id}/profile")
async def get_auth_profile(user_id: str) -> dict:
    """Exposure of the stored behavioural baseline (for dashboards/SOC)."""
    from app.auth_guard import get_auth_guard

    profile = get_auth_guard().get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No baseline profile for {user_id}")
    return {"user_id": user_id, **profile}
