"""API security tests: CORS allowlist and X-API-Key gate."""

from fastapi.testclient import TestClient

from app import main


def _client() -> TestClient:
    with TestClient(main.app) as live:
        return live


def test_cors_attacker_origin_gets_no_allow_header():
    client = _client()
    response = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") is None


def test_cors_allowed_origin_is_echoed():
    client = _client()
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_write_routes_open_without_api_key(monkeypatch):
    monkeypatch.setattr(main.settings, "API_KEY", "")
    client = _client()
    response = client.post(
        "/v1/auth-events",
        json={
            "user_id": "u1",
            "device_id": "d1",
            "ip_address": "10.0.0.1",
        },
    )
    assert response.status_code == 200


def test_write_routes_reject_wrong_key(monkeypatch):
    monkeypatch.setattr(main.settings, "API_KEY", "secret-123")
    client = _client()
    response = client.post(
        "/v1/auth-events",
        json={"user_id": "u1", "device_id": "d1", "ip_address": "10.0.0.1"},
    )
    assert response.status_code == 401

    ok = client.post(
        "/v1/auth-events",
        json={"user_id": "u1", "device_id": "d1", "ip_address": "10.0.0.1"},
        headers={"X-API-Key": "secret-123"},
    )
    assert ok.status_code == 200
    assert ok.json()["decision"] == "ALLOW"


def test_transactions_route_gated_too(monkeypatch):
    monkeypatch.setattr(main.settings, "API_KEY", "secret-123")
    client = _client()
    response = client.post(
        "/v1/transactions",
        json={
            "transaction_id": "t-1",
            "user_id": "u1",
            "amount": 499.0,
            "timestamp": "2026-02-10T10:00:00+00:00",
            "merchant_id": "m-77",
            "device_id": "d1",
            "ip_address": "10.0.0.5",
            "location_lat": 12.97,
            "location_long": 77.59,
        },
    )
    assert response.status_code == 401
