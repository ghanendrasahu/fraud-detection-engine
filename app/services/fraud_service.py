"""Fraud service orchestrating feature store, graph, ML, rules, and investigator."""

from __future__ import annotations

from app.feature_store import FeatureStore
from app.graph_engine import GraphEngine
from app.investigator import generate_investigator_summary
from app.logging_config import get_logger
from app.ml_engine import MLEngine
from app.rules import evaluate_decision
from app.schemas import (
    GraphResponse,
    TransactionEvent,
    TransactionFeatures,
    TransactionResponse,
)

logger = get_logger(__name__)


class FraudService:
    """Orchestrates the complete fraud detection pipeline."""

    def __init__(self) -> None:
        self.feature_store = FeatureStore()
        self.graph_engine = GraphEngine()
        self.ml_engine = MLEngine()

    def process_transaction(self, txn: TransactionEvent) -> TransactionResponse:
        """Run the full pipeline: features → graph → ML → rules → response."""
        logger.info(
            "Processing transaction user=%s amount=%.0f",
            txn.user_id, txn.amount,
        )

        # 1. Compute features
        raw_features = self.feature_store.compute_features(txn)
        features = TransactionFeatures(**raw_features)

        # 2. Update feature store with this transaction
        self.feature_store.add_transaction(txn.user_id, txn)

        # 3. Graph analysis
        self.graph_engine.add_transaction(txn.user_id, txn.device_id, txn.ip_address)
        graph_penalty = self.graph_engine.compute_graph_penalty(
            txn.user_id, txn.device_id, txn.ip_address
        )
        graph_data = self.graph_engine.get_2hop_neighborhood(txn.user_id)

        # 4. ML prediction
        ml_input = {
            "amount": float(txn.amount),
            "account_velocity_1h": float(features.account_velocity_1h),
            "amount_sum_24h": float(features.amount_sum_24h),
            "speed_kmh": float(features.speed_kmh),
            "is_new_device": 1.0 if features.is_new_device else 0.0,
        }
        ml_result = self.ml_engine.predict_risk(ml_input)
        ml_risk_score = ml_result["risk_score"]

        # 5. Decision
        decision, reasons = evaluate_decision(ml_risk_score, graph_penalty, ml_input)

        # 6. Investigator summary
        summary = generate_investigator_summary(
            txn, features, ml_risk_score, graph_penalty, reasons, decision
        )

        logger.info(
            "decision=%s ml_risk=%.3f graph_penalty=%.0f reasons=%d",
            decision.value, ml_risk_score, graph_penalty, len(reasons),
        )

        return TransactionResponse(
            transaction_id=txn.transaction_id,
            decision=decision,
            ml_risk_score=ml_risk_score,
            graph_penalty=graph_penalty,
            features=features,
            reason_codes=reasons,
            graph=GraphResponse(
                nodes=graph_data.get("nodes", []),
                edges=graph_data.get("edges", []),
                graph_penalty=graph_penalty,
            ),
            investigator_summary=summary,
        )

    def get_transaction_decision(self, transaction_id: str) -> TransactionResponse | None:
        """Retrieve a previously processed transaction decision (stub)."""
        # In production this would query a database. For MVP we return None.
        return None

    def health_check(self) -> dict[str, str]:
        return {
            "redis": self.feature_store.health_check(),
            "model": self.ml_engine.health_check(),
            "graph": self.graph_engine.health_check(),
        }
