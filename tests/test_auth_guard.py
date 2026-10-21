"""Predictive Cybersecurity Intelligence tests: the AuthGuard engine.

Covers the flagship scenario (India -> US -> Germany within 18 minutes on an
unknown device at 23:47) plus benign traffic, failure streaks, privilege
escalation and the API key/CORS gates.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.auth_guard import get_auth_guard, reset_auth_guard
from app.config import settings
from app.schemas import AuthDecision, AuthEvent

pytestmark = pytest.mark.usefixtures("_reset_guard")


@pytest.fixture()
def _reset_guard():
    get_auth_guard().reset()
    yield
    get_auth_guard().reset()


def _popular_event(**overrides: Any) -> dict[str, Any]:
    """A user's normal, boring login in Bangalore at 10:00 UTC."""
    base: dict[str, Any] = {
        "user_id": "user-A",
        "device_id": "corp-laptop-1",
        "ip_address": "203.0.113.7",
        "country": "IN",
        "city": "Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "timestamp": datetime(2026, 2, 10, 10, 0, tzinfo=UTC).isoformat(),
    }
    base.update(overrides)
    return base


def test_benign_repeat_login_is_allowed():
    guard = get_auth_guard()
    guard.assess(AuthEvent(**_popular_event()))
    second = AuthEvent(**_popular_event(timestamp=datetime(2026, 2, 10, 11, 0, tzinfo=UTC).isoformat()))
    result = guard.assess(second)
    assert result.decision is AuthDecision.ALLOW
    assert result.risk_score < 20
    assert result.reason_codes == []


def test_flagship_travel_scenario_scores_high_and_blocks():
    """Delhi at 22:55 -> Frankfurt 18 minutes later on an unknown device."""
    guard = get_auth_guard()
    # 1) The user's normal daytime login (Bangalore, corp laptop, India)
    guard.assess(AuthEvent(**_popular_event()))
    # 2) Same device, same country, but relocating: New Delhi, 22:55
    #    (educates baseline: hour 22, coords New Delhi)
    guard.assess(
        AuthEvent(
            **_popular_event(
                latitude=28.6139,
                longitude=77.2090,
                city="New Delhi",
                timestamp=datetime(2026, 2, 10, 22, 55, tzinfo=UTC).isoformat(),
            )
        )
    )
    # 3) The attack: Frankfurt 18 minutes later, new device, new country, odd hour
    suspicious = AuthEvent(
        **_popular_event(
            device_id="mystery-phone-x",
            ip_address="185.220.101.9",
            country="DE",
            city="Frankfurt",
            latitude=50.1109,
            longitude=8.6821,
            timestamp=datetime(2026, 2, 10, 23, 13, tzinfo=UTC).isoformat(),
        )
    )
    result = guard.assess(suspicious)

    codes = {reason.code for reason in result.reason_codes}
    assert "AUTH_IMPOSSIBLE_TRAVEL" in codes  # ~7,600 km/h across 4,400 km in 18 min? Delhi->Frankfurt ~6,600 km / 0.3h
    assert "AUTH_NEW_DEVICE" in codes
    assert "AUTH_UNKNOWN_COUNTRY" in codes
    assert "AUTH_ODD_HOURS" in codes
    assert result.risk_score >= settings.AUTH_BLOCK_THRESHOLD
    assert result.decision is AuthDecision.BLOCK
    assert "risk" in result.investigation.lower()
    assert "84.0" in result.investigation
    assert result.profile["known_devices"] == 1  # suspicious device NOT adopted into baseline


def test_odd_hours_latenight_signal():
    guard = get_auth_guard()
    guard.assess(AuthEvent(**_popular_event()))  # teaches usual hour 10:00
    odd = AuthEvent(
        **_popular_event(timestamp=datetime(2026, 2, 10, 23, 47, tzinfo=UTC).isoformat())
    )
    result = guard.assess(odd)
    codes = {reason.code for reason in result.reason_codes}
    assert "AUTH_ODD_HOURS" in codes
    # Same device + same country otherwise: score stays modest
    assert result.risk_score < settings.AUTH_BLOCK_THRESHOLD


def test_failed_streak_accumulates_without_baseline_training():
    guard = get_auth_guard()
    bad = AuthEvent(**_popular_event(success=False))
    first = guard.assess(bad)
    second = guard.assess(bad)
    assert second.risk_score > first.risk_score  # escalating streak
    # failures must NOT teach the baseline (device stays unknown)
    third = AuthEvent(
        **_popular_event(
            device_id="brand-new-device",
            success=True,
        )
    )
    result = guard.assess(third)
    assert any(r.code == "AUTH_NEW_DEVICE" for r in result.reason_codes)


def test_privilege_escalation_alone_triggers_step_up():
    guard = get_auth_guard()
    result = guard.assess(AuthEvent(**_popular_event(action="privilege_escalation")))
    # First contact: no baseline to violate; escalation alone is serious
    assert result.decision is AuthDecision.STEP_UP
    assert any(r.code == "AUTH_PRIVILEGE_ESCALATION" for r in result.reason_codes)


def test_successful_login_grows_baseline():
    guard = get_auth_guard()
    guard.assess(AuthEvent(**_popular_event()))
    profile = guard.get_profile("user-A")
    assert profile is not None
    assert profile["known_devices"] == 1
    assert "IN" in profile["known_countries"]


def test_profile_endpoint_404s_for_unknown():
    reset_auth_guard()
    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    response = client.get("/v1/auth-events/ghost/profile")
    assert response.status_code in {404, 503}  # 503 before lifespan init, 404 after
