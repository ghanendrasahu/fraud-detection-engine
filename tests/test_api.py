"""Tests for FastAPI endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.services.fraud_service import FraudService

# Ensure fraud_service is initialized for tests
if main_module.fraud_service is None:
    main_module.fraud_service = FraudService()

client = TestClient(app)

VALID_TRANSACTION = {
    "transaction_id": "txn_test_api_001",
    "user_id": "user_1001",
    "amount": 85000,
    "timestamp": "2026-09-18T14:30:00Z",
    "merchant_id": "merchant_001",
    "device_id": "device_suspicious_01",
    "ip_address": "10.10.10.10",
    "location_lat": 12.9716,
    "location_long": 77.5946,
}


class TestHealthEndpoint:
    def test_health_returns_200(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "starting")
        assert "redis" in data
        assert "model" in data
        assert "graph" in data


class TestTransactionEndpoint:
    def test_valid_transaction(self) -> None:
        resp = client.post("/v1/transactions", json=VALID_TRANSACTION)
        assert resp.status_code == 200
        data = resp.json()
        assert data["transaction_id"] == "txn_test_api_001"
        assert data["decision"] in ("APPROVED", "INVESTIGATION_REQUIRED")
        assert 0 <= data["ml_risk_score"] <= 1
        assert 0 <= data["graph_penalty"] <= 100
        assert "features" in data
        assert "reason_codes" in data
        assert "graph" in data
        assert "investigator_summary" in data

    def test_invalid_amount_zero(self) -> None:
        txn = VALID_TRANSACTION.copy()
        txn["transaction_id"] = "txn_test_zero"
        txn["amount"] = 0
        resp = client.post("/v1/transactions", json=txn)
        assert resp.status_code == 422

    def test_invalid_amount_negative(self) -> None:
        txn = VALID_TRANSACTION.copy()
        txn["transaction_id"] = "txn_test_neg"
        txn["amount"] = -100
        resp = client.post("/v1/transactions", json=txn)
        assert resp.status_code == 422

    def test_invalid_latitude(self) -> None:
        txn = VALID_TRANSACTION.copy()
        txn["transaction_id"] = "txn_test_lat"
        txn["location_lat"] = 91.0
        resp = client.post("/v1/transactions", json=txn)
        assert resp.status_code == 422

    def test_invalid_longitude(self) -> None:
        txn = VALID_TRANSACTION.copy()
        txn["transaction_id"] = "txn_test_lon"
        txn["location_long"] = 181.0
        resp = client.post("/v1/transactions", json=txn)
        assert resp.status_code == 422

    def test_missing_required_field(self) -> None:
        txn = VALID_TRANSACTION.copy()
        del txn["user_id"]
        resp = client.post("/v1/transactions", json=txn)
        assert resp.status_code == 422

    def test_response_schema_matches(self) -> None:
        resp = client.post("/v1/transactions", json=VALID_TRANSACTION)
        data = resp.json()
        assert isinstance(data["reason_codes"], list)
        for rc in data["reason_codes"]:
            assert "code" in rc
            assert "message" in rc
            assert "severity" in rc
            assert "source" in rc


class TestModelInfoEndpoint:
    def test_model_info(self) -> None:
        resp = client.get("/v1/model/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "model_type" in data
        assert "features" in data
        assert "threshold" in data
        assert "onnx_available" in data
