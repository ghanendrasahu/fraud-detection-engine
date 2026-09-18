"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.kafka_producer import kafka_producer
from app.logging_config import get_logger, setup_logging
from app.schemas import (
    HealthResponse,
    ModelInfoResponse,
    TransactionEvent,
    TransactionResponse,
)
from app.services.fraud_service import FraudService

logger = get_logger(__name__)

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
    allow_origins=["*"],
    allow_credentials=True,
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


@app.post("/v1/transactions", response_model=TransactionResponse)
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
