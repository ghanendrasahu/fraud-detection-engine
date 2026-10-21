"""Identity / authentication anomaly engine.

Baseline-profile approach ("Predictive Cybersecurity Intelligence"):
each user's known devices, countries, login hours and last known geo are
tracked; every incoming AuthEvent is scored against that baseline with
deterministic reason codes (same style as the transaction rule engine) and a
compound-risk multiplier when multiple weak signals co-occur.

Scores:
- new device ...... +12
- unknown country . +15
- odd hours (0-5) . +8
- impossible travel +35 (haversine / elapsed > AUTH_MAX_SPEED)
- failed attempt ... +12 per consecutive failure (cap 30)
- mfa change ....... +20
- privilege escalation +40
3+ weak signals together get a 1.2x compounding multiplier (capped 99.5).

Storage is an in-memory profile map (bounded, thread-safe). A Redis-backed
implementation should keep the same interface.
"""

from __future__ import annotations

import math
import threading
from collections import OrderedDict, deque
from datetime import UTC, datetime
from typing import Any

from app.config import settings
from app.logging_config import get_logger
from app.schemas import (
    AuthAssessment,
    AuthDecision,
    AuthEvent,
    ReasonCode,
    Severity,
)

logger = get_logger(__name__)

_MAX_PROFILES = 10_000
# Late-night hours: 23:00-04:59 UTC. Anything else counts as "usual day".
_ODD_HOURS = frozenset({23, 0, 1, 2, 3, 4})

_WEIGHT_DEVICE = 12.0
_WEIGHT_COUNTRY = 15.0
_WEIGHT_ODD_HOURS = 8.0
_WEIGHT_TRAVEL = 35.0
_WEIGHT_FAILED = 12.0
_CAP_FAILED = 30.0
_WEIGHT_MFA = 20.0
_WEIGHT_ESCALATION = 40.0
_COMPOUND_MULTIPLIER = 1.2
_COMPOUND_MIN_SIGNALS = 3


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points, in kilometres."""
    rad = math.pi / 180.0
    dlat, dlon = (lat2 - lat1) * rad, (lon2 - lon1) * rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2) ** 2
    )
    return 6371.0088 * 2 * math.asin(math.sqrt(min(a, 1.0)))


class AuthProfile:
    """Rolling baseline of one user's normal identity behaviour."""

    __slots__ = ("countries", "devices", "failed_streak", "first_seen", "hours", "last_lat", "last_lon", "last_ts", "user_id")

    def __init__(self, user_id: str, now: datetime) -> None:
        self.user_id = user_id
        self.devices: set[str] = set()
        self.countries: set[str] = set()
        self.hours: deque[int] = deque(maxlen=50)
        self.failed_streak = 0
        self.last_lat: float | None = None
        self.last_lon: float | None = None
        self.last_ts: datetime | None = None
        self.first_seen = now

    def summary(self) -> dict[str, Any]:
        return {
            "known_devices": len(self.devices),
            "known_countries": sorted(self.countries),
            "usual_hours": sorted(set(self.hours))[-8:],
            "failed_streak": self.failed_streak,
            "first_seen": self.first_seen.isoformat(),
        }


class AuthGuard:
    """Scores identity events against per-user baselines."""

    def __init__(self) -> None:
        self._profiles: OrderedDict[str, AuthProfile] = OrderedDict()
        self._lock = threading.Lock()

    def reset(self) -> None:
        """Test hook - wipe all baselines."""
        with self._lock:
            self._profiles.clear()

    def get_profile(self, user_id: str) -> dict[str, Any] | None:
        if user_id not in self._profiles:
            return None
        with self._lock:
            profile = self._profiles[user_id]
            return profile.summary()

    def assess(self, event: AuthEvent) -> AuthAssessment:
        now = event.timestamp
        if now.tzinfo is None:  # tolerate naive timestamps as UTC
            now = now.replace(tzinfo=UTC)
        now = now.astimezone(UTC)
        with self._lock:
            profile = self._profiles.get(event.user_id)
            if profile is None:
                profile = AuthProfile(event.user_id, now)
                self._profiles[event.user_id] = profile
                self._profiles.move_to_end(event.user_id)
                if len(self._profiles) > _MAX_PROFILES:
                    self._profiles.popitem(last=False)
            else:
                self._profiles.move_to_end(event.user_id)

            signals: list[ReasonCode] = []
            added = 0.0

            is_first_contact = (
                not profile.devices and not profile.hours and profile.failed_streak == 0
            )
            if not is_first_contact and (event.is_new_device or event.device_id not in profile.devices):
                added += _WEIGHT_DEVICE
                signals.append(self._reason("AUTH_NEW_DEVICE", Severity.HIGH, f"Login from device {event.device_id} not in the user's history"))

            if event.country and profile.countries and event.country not in profile.countries:
                added += _WEIGHT_COUNTRY
                signals.append(self._reason("AUTH_UNKNOWN_COUNTRY", Severity.HIGH, f"First login from country {event.country}"))

            speed = self._travel_speed(profile, event, now)
            if speed is not None and speed > settings.AUTH_MAX_SPEED:
                added += _WEIGHT_TRAVEL
                signals.append(self._reason("AUTH_IMPOSSIBLE_TRAVEL", Severity.CRITICAL, f"Moved at {speed:,.0f} km/h - beyond human travel"))

            hour = now.hour
            if hour in _ODD_HOURS and profile.hours and hour not in profile.hours:
                added += _WEIGHT_ODD_HOURS
                signals.append(self._reason("AUTH_ODD_HOURS", Severity.MEDIUM, f"Login at {hour:02d}:00 UTC - outside the user's usual pattern"))

            if event.action.value == "mfa_change":
                added += _WEIGHT_MFA
                signals.append(self._reason("AUTH_MFA_CHANGE", Severity.HIGH, "MFA configuration changed"))
            if event.action.value == "privilege_escalation":
                added += _WEIGHT_ESCALATION
                signals.append(self._reason("AUTH_PRIVILEGE_ESCALATION", Severity.CRITICAL, "Privilege escalation attempt"))

            if not event.success:
                profile.failed_streak += 1
                penalty = min(_WEIGHT_FAILED * profile.failed_streak, _CAP_FAILED)
                added += penalty
                signals.append(self._reason("AUTH_FAILED_ATTEMPTS", Severity.HIGH, f"{profile.failed_streak} consecutive failed attempt(s)"))
                decision = self._decide(min(99.5, added))
                return self._assessment(decision, added, signals, profile)

            # Compound-risk multiplier when several weak signals co-occur.
            if len(signals) >= _COMPOUND_MIN_SIGNALS:
                added = min(added * _COMPOUND_MULTIPLIER, 99.5)

            decision = self._decide(added)

            # Baseline education: never teach from a BLOCKED event (an
            # attacker whose login succeeded must not become "normal").
            if decision is not AuthDecision.BLOCK:
                if hour not in profile.hours:
                    profile.hours.append(hour)
                profile.devices.add(event.device_id)
                if event.country:
                    profile.countries.add(event.country)
                profile.last_lat = event.latitude if event.latitude is not None else profile.last_lat
                profile.last_lon = event.longitude if event.longitude is not None else profile.last_lon
                profile.last_ts = now
                profile.failed_streak = 0

            logger.info("auth_event user=%s risk=%.1f decision=%s signals=%d", event.user_id, added, decision.value, len(signals))
            return self._assessment(decision, added, signals, profile)

    # ---------------- internals ----------------
    @staticmethod
    def _travel_speed(profile: AuthProfile, event: AuthEvent, now: datetime) -> float | None:
        if profile.last_lat is None or profile.last_ts is None:
            return None
        if event.latitude is None or event.longitude is None:
            return None
        elapsed_hours = (now - profile.last_ts).total_seconds() / 3600.0
        if elapsed_hours <= 0:
            return None
        distance = _haversine_km(profile.last_lat, profile.last_lon, event.latitude, event.longitude)
        return distance / max(elapsed_hours, 0.05)

    @staticmethod
    def _reason(code: str, severity: Severity, message: str) -> ReasonCode:
        return ReasonCode(code=code, message=message, severity=severity, source="AUTH_GUARD")

    @staticmethod
    def _decide(score: float) -> AuthDecision:
        if score >= settings.AUTH_BLOCK_THRESHOLD:
            return AuthDecision.BLOCK
        if score >= settings.AUTH_STEP_UP_THRESHOLD:
            return AuthDecision.STEP_UP
        return AuthDecision.ALLOW

    @staticmethod
    def _assessment(decision: AuthDecision, score: float, signals: list[ReasonCode], profile: AuthProfile) -> AuthAssessment:
        investigation = AuthGuard._narrative(decision, score, signals, profile)
        return AuthAssessment(
            risk_score=round(min(score, 99.5), 1),
            decision=decision,
            reason_codes=signals,
            investigation=investigation,
            profile=profile.summary(),
        )

    @staticmethod
    def _narrative(decision: AuthDecision, score: float, signals: list[ReasonCode], profile: AuthProfile) -> str:
        if not signals:
            return (f"Login consistent with this user's baseline of "
                    f"{len(profile.devices)} known device(s). Risk {score:.1f}/100.")
        worst = signals[0].message
        parts = [
            f"Identity risk {score:.1f}/100 -> {decision.value}.",
            f"Primary signal: {worst}",
        ]
        others = [sig.message for sig in signals[1:3]]
        if others:
            parts.append("Also observed: " + "; ".join(others))
        parts.append(f"Baseline: {len(profile.devices)} known device(s), "
                     f"{len(profile.countries)} known country/ies, "
                     f"{profile.failed_streak} recent failure(s).")
        return " ".join(parts)

    def __len__(self) -> int:
        return len(self._profiles)


_guard: AuthGuard | None = None


def get_auth_guard() -> AuthGuard:
    """Process-wide singleton (tests use ``.reset()``)."""
    global _guard
    if _guard is None:
        _guard = AuthGuard()
    return _guard


def reset_auth_guard() -> None:
    global _guard
    if _guard is not None:
        _guard.reset()
    _guard = None


__all__ = ["AuthGuard", "get_auth_guard", "reset_auth_guard"]
