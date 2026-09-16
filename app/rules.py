"""Deterministic rule engine for fraud decision."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.logging_config import get_logger
from app.schemas import Decision, ReasonCode, Severity

logger = get_logger(__name__)


def evaluate_decision(
    ml_risk_score: float,
    graph_penalty: float,
    features: dict[str, Any],
) -> tuple[Decision, list[ReasonCode]]:
    """
    Combine ML score, graph penalty, and feature flags into a final decision.

    Returns:
        (decision, reason_codes)
    """
    reasons: list[ReasonCode] = []

    # --- ML risk ---
    if ml_risk_score > settings.ML_RISK_THRESHOLD:
        reasons.append(
            ReasonCode(
                code="HIGH_ML_RISK",
                message=f"ML fraud risk score {ml_risk_score:.1%} exceeds threshold",
                severity=Severity.CRITICAL,
                source="ML_ENGINE",
            )
        )

    # --- Impossible travel ---
    speed = features.get("speed_kmh", 0)
    if speed > settings.IMPOSSIBLE_TRAVEL_SPEED:
        reasons.append(
            ReasonCode(
                code="IMPOSSIBLE_TRAVEL",
                message=f"Impossible travel detected at {speed:.0f} km/h",
                severity=Severity.CRITICAL,
                source="FEATURE_ENGINE",
            )
        )

    # --- Graph penalty ---
    if graph_penalty > settings.GRAPH_PENALTY_THRESHOLD:
        reasons.append(
            ReasonCode(
                code="HIGH_GRAPH_RISK",
                message=f"Graph penalty {graph_penalty:.0f}/100 exceeds threshold",
                severity=Severity.HIGH,
                source="GRAPH_ENGINE",
            )
        )

    # --- High velocity ---
    velocity = features.get("account_velocity_1h", 0)
    if velocity >= 5:
        reasons.append(
            ReasonCode(
                code="HIGH_VELOCITY",
                message=f"{velocity} transactions in the last hour",
                severity=Severity.HIGH if velocity >= 8 else Severity.MEDIUM,
                source="FEATURE_ENGINE",
            )
        )

    # --- High 24h volume ---
    amount_24h = features.get("amount_sum_24h", 0)
    if amount_24h > 100000:
        reasons.append(
            ReasonCode(
                code="HIGH_24H_VOLUME",
                message=f"24-hour transaction volume ₹{amount_24h:,.0f}",
                severity=Severity.HIGH if amount_24h > 500000 else Severity.MEDIUM,
                source="FEATURE_ENGINE",
            )
        )

    # --- New device ---
    if features.get("is_new_device", False):
        reasons.append(
            ReasonCode(
                code="NEW_DEVICE",
                message="New device identified",
                severity=Severity.MEDIUM,
                source="FEATURE_ENGINE",
            )
        )

    # --- Suspicious connections (from graph penalty breakdown) ---
    if graph_penalty >= 80:
        reasons.append(
            ReasonCode(
                code="SUSPICIOUS_DEVICE",
                message="Connected to suspicious device",
                severity=Severity.HIGH,
                source="GRAPH_ENGINE",
            )
        )
    if 70 <= graph_penalty < 80 or (graph_penalty >= 80 and "SUSPICIOUS_DEVICE" not in [r.code for r in reasons]):
        if graph_penalty >= 70:
            reasons.append(
                ReasonCode(
                    code="SUSPICIOUS_IP",
                    message="Connected to suspicious IP address",
                    severity=Severity.HIGH,
                    source="GRAPH_ENGINE",
                )
            )
    if graph_penalty >= 60 and graph_penalty < 70:
        reasons.append(
            ReasonCode(
                code="SUSPICIOUS_CONNECTION",
                message="Connected to a suspicious account",
                severity=Severity.MEDIUM,
                source="GRAPH_ENGINE",
            )
        )

    # --- Final decision ---
    investigate = (
        ml_risk_score > settings.ML_RISK_THRESHOLD
        or speed > settings.IMPOSSIBLE_TRAVEL_SPEED
        or graph_penalty > settings.GRAPH_PENALTY_THRESHOLD
    )

    decision = Decision.INVESTIGATION_REQUIRED if investigate else Decision.APPROVED

    logger.info("decision=%s ml_risk=%.3f graph_penalty=%.0f reasons=%d",
                decision.value, ml_risk_score, graph_penalty, len(reasons))

    return decision, reasons
