"""Feature store with Redis backend and in-memory fallback."""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Haversine formula
# ---------------------------------------------------------------------------

EARTH_RADIUS_KM = 6371.0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in km between two points."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


# ---------------------------------------------------------------------------
# In-memory fallback store
# ---------------------------------------------------------------------------

class InMemoryStore:
    """Thread-unsafe in-memory store mimicking Redis sorted-set semantics."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, float]] = {}
        self._strings: dict[str, str] = {}
        self._sets: dict[str, set[str]] = {}

    def zadd(self, key: str, mapping: dict[str, float]) -> int:
        if key not in self._data:
            self._data[key] = {}
        count = 0
        for member, score in mapping.items():
            if member not in self._data[key]:
                count += 1
            self._data[key][member] = score
        return count

    def zrangebyscore(self, key: str, min_score: float, max_score: float) -> list[str]:
        if key not in self._data:
            return []
        return [
            member
            for member, score in sorted(self._data[key].items(), key=lambda x: x[1])
            if min_score <= score <= max_score
        ]

    def zcard(self, key: str) -> int:
        return len(self._data.get(key, {}))

    def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        if key not in self._data:
            return 0
        to_remove = [
            m for m, s in self._data[key].items() if min_score <= s <= max_score
        ]
        for m in to_remove:
            del self._data[key][m]
        return len(to_remove)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._strings[key] = value

    def get(self, key: str) -> Optional[str]:
        return self._strings.get(key)

    def set(self, key: str, value: str) -> None:
        self._strings[key] = value

    def delete(self, key: str) -> None:
        self._strings.pop(key, None)
        self._data.pop(key, None)

    def smembers(self, key: str) -> set[str]:
        return self._sets.get(key, set()).copy()

    def sadd(self, key: str, *members: str) -> int:
        if key not in self._sets:
            self._sets[key] = set()
        added = 0
        for m in members:
            if m not in self._sets[key]:
                self._sets[key].add(m)
                added += 1
        return added

    def sismember(self, key: str, member: str) -> bool:
        return member in self._sets.get(key, set())


# ---------------------------------------------------------------------------
# Feature Store
# ---------------------------------------------------------------------------

class FeatureStore:
    """Extracts behavioral features from transaction history stored in Redis."""

    def __init__(self) -> None:
        self._redis_client: Any = None  # type: ignore[assignment]
        self._fallback = InMemoryStore()
        self._use_fallback = True
        self._try_connect()

    def _try_connect(self) -> None:
        try:
            import redis as redis_lib  # type: ignore[import-untyped]
            self._redis_client = redis_lib.from_url(
                settings.REDIS_URL, decode_responses=True, socket_timeout=2
            )
            self._redis_client.ping()
            self._use_fallback = False
            logger.info("Connected to Redis at %s", settings.REDIS_URL)
        except Exception:
            logger.warning("Redis unavailable – using in-memory fallback")
            self._use_fallback = True

    def _get_store(self) -> Any:
        return self._fallback if self._use_fallback else self._redis_client

    # ---- helpers ----------------------------------------------------------

    def _txn_key(self, user_id: str) -> str:
        return f"txn:{user_id}"

    def _device_key(self, user_id: str) -> str:
        return f"devices:{user_id}"

    def _location_key(self, user_id: str) -> str:
        return f"location:{user_id}"

    def _ts(self, dt: datetime) -> float:
        return dt.timestamp()

    # ---- public API -------------------------------------------------------

    def add_transaction(self, user_id: str, transaction: Any) -> None:
        """Record a transaction in the feature store."""
        store = self._get_store()
        key = self._txn_key(user_id)
        ts = self._ts(transaction.timestamp)
        member = json.dumps({
            "transaction_id": transaction.transaction_id,
            "amount": transaction.amount,
            "timestamp": ts,
            "lat": transaction.location_lat,
            "lon": transaction.location_long,
            "device_id": transaction.device_id,
            "ip_address": transaction.ip_address,
        })

        if self._use_fallback:
            store.zadd(key, {member: ts})
        else:
            store.zadd(key, {member: ts})
            store.expire(key, settings.TRANSACTION_HISTORY_TTL)

        # Track devices
        dev_key = self._device_key(user_id)
        if self._use_fallback:
            store.sadd(dev_key, transaction.device_id)
        else:
            store.sadd(dev_key, transaction.device_id)
            store.expire(dev_key, settings.DEVICE_TTL)

        # Track location
        loc_key = self._location_key(user_id)
        loc_data = json.dumps({
            "lat": transaction.location_lat,
            "lon": transaction.location_long,
            "timestamp": ts,
        })
        if self._use_fallback:
            store.set(loc_key, loc_data)
        else:
            store.setex(loc_key, settings.LOCATION_TTL, loc_data)

    def compute_features(self, transaction: Any) -> dict[str, Any]:
        """Compute features for the given transaction."""
        store = self._get_store()
        now = transaction.timestamp
        user_id = transaction.user_id

        # -- account velocity (1h) --
        one_hour_ago = self._ts(now - timedelta(hours=1))
        current_ts = self._ts(now)
        key = self._txn_key(user_id)

        if self._use_fallback:
            recent = store.zrangebyscore(key, one_hour_ago, current_ts)
        else:
            recent = store.zrangebyscore(key, one_hour_ago, current_ts)

        account_velocity_1h = len(recent)

        # -- amount sum 24h --
        twenty_four_hours_ago = self._ts(now - timedelta(hours=24))
        if self._use_fallback:
            all_24h = store.zrangebyscore(key, twenty_four_hours_ago, current_ts)
        else:
            all_24h = store.zrangebyscore(key, twenty_four_hours_ago, current_ts)

        amount_sum_24h = sum(
            json.loads(m).get("amount", 0) for m in all_24h
        )

        # -- is new device --
        dev_key = self._device_key(user_id)
        if self._use_fallback:
            known_devices = store.smembers(dev_key)
        else:
            known_devices = store.smembers(dev_key)

        is_new_device = transaction.device_id not in known_devices

        # -- speed / impossible travel --
        loc_key = self._location_key(user_id)
        speed_kmh = 0.0
        prev_lat: float | None = None
        prev_lon: float | None = None
        prev_ts: datetime | None = None

        if self._use_fallback:
            prev_loc_raw = store.get(loc_key)
        else:
            prev_loc_raw = store.get(loc_key)

        if prev_loc_raw:
            prev_loc = json.loads(prev_loc_raw)
            prev_lat = prev_loc["lat"]
            prev_lon = prev_loc["lon"]
            from datetime import timezone as _tz
            prev_ts_dt = datetime.fromtimestamp(prev_loc["timestamp"], tz=_tz.utc)
            prev_ts = prev_ts_dt
            elapsed_hours = (now - prev_ts_dt).total_seconds() / 3600.0

            if elapsed_hours > 0 and prev_lat is not None and prev_lon is not None:
                dist = haversine(prev_lat, prev_lon, transaction.location_lat, transaction.location_long)
                speed_kmh = dist / elapsed_hours
            else:
                speed_kmh = 0.0

        return {
            "account_velocity_1h": max(0, account_velocity_1h),
            "amount_sum_24h": round(amount_sum_24h, 2),
            "is_new_device": is_new_device,
            "speed_kmh": round(speed_kmh, 2),
            "previous_location_lat": prev_lat,
            "previous_location_long": prev_lon,
            "previous_timestamp": prev_ts,
        }

    def health_check(self) -> str:
        """Return health status of the underlying store."""
        if self._use_fallback:
            return "in_memory"
        try:
            self._redis_client.ping()
            return "connected"
        except Exception:
            return "error"
