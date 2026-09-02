"""Pydantic schemas for request/response validation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class Decision(str, Enum):
    """Fraud decision outcomes."""

    APPROVED = "APPROVED"
    INVESTIGATION_REQUIRED = "INVESTIGATION_REQUIRED"


class Severity(str, Enum):
    """Reason code severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TransactionEvent(BaseModel):
    """Incoming transaction event."""

    transaction_id: str = Field(..., min_length=1, max_length=64)
    user_id: str = Field(..., min_length=1, max_length=64)
    amount: float = Field(..., gt=0, description="Transaction amount in INR")
    timestamp: datetime
    merchant_id: str = Field(..., min_length=1, max_length=64)
    device_id: str = Field(..., min_length=1, max_length=64)
    ip_address: str = Field(..., min_length=1, max_length=45)
    location_lat: float = Field(..., ge=-90, le=90)
    location_long: float = Field(..., ge=-180, le=180)

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class TransactionFeatures(BaseModel):
    """Computed features for a transaction."""

    account_velocity_1h: int = Field(default=0, ge=0)
    amount_sum_24h: float = Field(default=0.0, ge=0)
    is_new_device: bool = Field(default=True)
    speed_kmh: float = Field(default=0.0, ge=0)
    previous_location_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    previous_location_long: Optional[float] = Field(default=None, ge=-180, le=180)
    previous_timestamp: Optional[datetime] = None


class ReasonCode(BaseModel):
    """A single reason code explaining the decision."""

    code: str
    message: str
    severity: Severity
    source: str = Field(default="RULE_ENGINE")


class FraudDecision(BaseModel):
    """Complete fraud decision output."""

    transaction_id: str
    decision: Decision
    ml_risk_score: float = Field(..., ge=0, le=1)
    graph_penalty: float = Field(default=0.0, ge=0, le=100)
    features: TransactionFeatures
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    investigator_summary: str = Field(default="")


class GraphNode(BaseModel):
    """Graph node for visualization."""

    id: str
    label: str
    node_type: str  # USER, DEVICE, IP
    suspicious: bool = False


class GraphEdge(BaseModel):
    """Graph edge for visualization."""

    source: str
    target: str
    relationship: str  # USES, CONNECTED_FROM, SEEN_WITH, USED_BY


class GraphResponse(BaseModel):
    """Graph data for API response."""

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    graph_penalty: float = Field(default=0.0, ge=0, le=100)


class FeatureContribution(BaseModel):
    """Feature contribution for explainability."""

    feature: str
    contribution: float


class TransactionResponse(BaseModel):
    """API response for transaction processing."""

    transaction_id: str
    decision: Decision
    ml_risk_score: float = Field(..., ge=0, le=1)
    graph_penalty: float = Field(default=0.0, ge=0, le=100)
    features: TransactionFeatures
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    graph: GraphResponse = Field(default_factory=GraphResponse)
    investigator_summary: str = Field(default="")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    redis: str = "unknown"
    model: str = "unknown"
    graph: str = "unknown"


class ModelInfoResponse(BaseModel):
    """Model information response."""

    model_type: str
    features: list[str]
    threshold: float
    onnx_available: bool
