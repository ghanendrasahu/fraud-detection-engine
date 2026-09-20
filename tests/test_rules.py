"""Tests for the rule engine."""

from __future__ import annotations

import pytest  # type: ignore[import-untyped]

from app.rules import evaluate_decision
from app.schemas import Decision


class TestRuleEngine:
    """Test fraud decision rules."""

    def test_approved_low_risk(self) -> None:
        decision, reasons = evaluate_decision(
            ml_risk_score=0.2,
            graph_penalty=0,
            features={"speed_kmh": 0, "account_velocity_1h": 1, "amount_sum_24h": 5000, "is_new_device": False, "amount": 2000},
        )
        assert decision == Decision.APPROVED
        assert len(reasons) == 0

    def test_investigation_high_ml_risk(self) -> None:
        decision, reasons = evaluate_decision(
            ml_risk_score=0.95,
            graph_penalty=0,
            features={"speed_kmh": 0, "account_velocity_1h": 1, "amount_sum_24h": 5000, "is_new_device": False, "amount": 2000},
        )
        assert decision == Decision.INVESTIGATION_REQUIRED
        codes = [r.code for r in reasons]
        assert "HIGH_ML_RISK" in codes

    def test_investigation_impossible_travel(self) -> None:
        decision, reasons = evaluate_decision(
            ml_risk_score=0.3,
            graph_penalty=0,
            features={"speed_kmh": 1200, "account_velocity_1h": 1, "amount_sum_24h": 5000, "is_new_device": False, "amount": 2000},
        )
        assert decision == Decision.INVESTIGATION_REQUIRED
        codes = [r.code for r in reasons]
        assert "IMPOSSIBLE_TRAVEL" in codes

    def test_investigation_high_graph_penalty(self) -> None:
        decision, reasons = evaluate_decision(
            ml_risk_score=0.4,
            graph_penalty=80,
            features={"speed_kmh": 0, "account_velocity_1h": 1, "amount_sum_24h": 5000, "is_new_device": False, "amount": 2000},
        )
        assert decision == Decision.INVESTIGATION_REQUIRED
        codes = [r.code for r in reasons]
        assert "HIGH_GRAPH_RISK" in codes

    def test_high_velocity_reason(self) -> None:
        decision, reasons = evaluate_decision(
            ml_risk_score=0.3,
            graph_penalty=0,
            features={"speed_kmh": 0, "account_velocity_1h": 7, "amount_sum_24h": 5000, "is_new_device": False, "amount": 2000},
        )
        codes = [r.code for r in reasons]
        assert "HIGH_VELOCITY" in codes

    def test_new_device_reason(self) -> None:
        decision, reasons = evaluate_decision(
            ml_risk_score=0.3,
            graph_penalty=0,
            features={"speed_kmh": 0, "account_velocity_1h": 1, "amount_sum_24h": 5000, "is_new_device": True, "amount": 2000},
        )
        codes = [r.code for r in reasons]
        assert "NEW_DEVICE" in codes

    def test_multiple_reasons(self) -> None:
        decision, reasons = evaluate_decision(
            ml_risk_score=0.92,
            graph_penalty=75,
            features={"speed_kmh": 1500, "account_velocity_1h": 8, "amount_sum_24h": 200000, "is_new_device": True, "amount": 85000},
        )
        assert decision == Decision.INVESTIGATION_REQUIRED
        assert len(reasons) >= 4

    def test_boundary_ml_risk(self) -> None:
        # Exactly at threshold should be approved
        decision, _ = evaluate_decision(
            ml_risk_score=0.85,
            graph_penalty=0,
            features={"speed_kmh": 0, "account_velocity_1h": 1, "amount_sum_24h": 5000, "is_new_device": False, "amount": 2000},
        )
        assert decision == Decision.APPROVED

    def test_boundary_graph_penalty(self) -> None:
        # Exactly at threshold should be approved
        decision, _ = evaluate_decision(
            ml_risk_score=0.3,
            graph_penalty=70,
            features={"speed_kmh": 0, "account_velocity_1h": 1, "amount_sum_24h": 5000, "is_new_device": False, "amount": 2000},
        )
        assert decision == Decision.APPROVED
