"""Tests for feature store and Haversine calculations."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest  # type: ignore[import-untyped]

from app.feature_store import FeatureStore, haversine


class TestHaversine:
    """Test the Haversine distance formula."""

    def test_same_point(self) -> None:
        assert haversine(12.9716, 77.5946, 12.9716, 77.5946) == 0.0

    def test_known_distance(self) -> None:
        # Mumbai to Delhi ~1150 km
        dist = haversine(19.0760, 72.8777, 28.7041, 77.1025)
        assert 1100 < dist < 1250

    def test_symmetry(self) -> None:
        d1 = haversine(12.9716, 77.5946, 28.7041, 77.1025)
        d2 = haversine(28.7041, 77.1025, 12.9716, 77.5946)
        assert abs(d1 - d2) < 0.01

    def test_opposite_points(self) -> None:
        dist = haversine(0, 0, 0, 180)
        assert 20000 < dist < 21000  # ~half circumference


class TestFeatureStore:
    """Test feature computation with in-memory fallback."""

    def setup_method(self) -> None:
        self.store = FeatureStore()
        assert self.store._use_fallback  # ensure in-memory mode

    def _make_txn(self, **overrides) -> object:
        defaults = {
            "transaction_id": "txn_test_001",
            "user_id": "user_test",
            "amount": 5000.0,
            "timestamp": datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc),
            "merchant_id": "merchant_001",
            "device_id": "device_001",
            "ip_address": "10.0.0.1",
            "location_lat": 12.9716,
            "location_long": 77.5946,
        }
        defaults.update(overrides)

        class T:
            pass

        t = T()
        for k, v in defaults.items():
            setattr(t, k, v)
        return t

    def test_velocity_empty_history(self) -> None:
        txn = self._make_txn()
        features = self.store.compute_features(txn)
        assert features["account_velocity_1h"] == 0

    def test_velocity_after_transactions(self) -> None:
        now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
        txn1 = self._make_txn(transaction_id="txn_1", timestamp=now - timedelta(minutes=30))
        txn2 = self._make_txn(transaction_id="txn_2", timestamp=now - timedelta(minutes=10))
        txn3 = self._make_txn(transaction_id="txn_3", timestamp=now)

        self.store.add_transaction("user_test", txn1)
        self.store.add_transaction("user_test", txn2)
        features = self.store.compute_features(txn3)
        assert features["account_velocity_1h"] == 2

    def test_is_new_device(self) -> None:
        txn = self._make_txn(device_id="device_new")
        features = self.store.compute_features(txn)
        assert features["is_new_device"] is True

    def test_known_device(self) -> None:
        now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
        txn1 = self._make_txn(device_id="device_known", timestamp=now - timedelta(hours=2))
        self.store.add_transaction("user_test", txn1)

        txn2 = self._make_txn(device_id="device_known", timestamp=now)
        features = self.store.compute_features(txn2)
        assert features["is_new_device"] is False

    def test_speed_zero_initial(self) -> None:
        txn = self._make_txn()
        features = self.store.compute_features(txn)
        assert features["speed_kmh"] == 0.0

    def test_impossible_travel(self) -> None:
        # First transaction in Mumbai
        now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
        txn1 = self._make_txn(
            transaction_id="txn_1",
            location_lat=19.0760,
            location_long=72.8777,
            timestamp=now - timedelta(minutes=15),
        )
        self.store.add_transaction("user_test", txn1)

        # Second transaction in Delhi 15 minutes later
        txn2 = self._make_txn(
            transaction_id="txn_2",
            location_lat=28.7041,
            location_long=77.1025,
            timestamp=now,
        )
        features = self.store.compute_features(txn2)
        assert features["speed_kmh"] > 800

    def test_amount_sum_24h(self) -> None:
        now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
        txn1 = self._make_txn(transaction_id="txn_1", amount=10000, timestamp=now - timedelta(hours=5))
        txn2 = self._make_txn(transaction_id="txn_2", amount=25000, timestamp=now - timedelta(hours=2))
        self.store.add_transaction("user_test", txn1)
        self.store.add_transaction("user_test", txn2)

        txn3 = self._make_txn(transaction_id="txn_3", amount=5000, timestamp=now)
        features = self.store.compute_features(txn3)
        assert features["amount_sum_24h"] == 35000.0
