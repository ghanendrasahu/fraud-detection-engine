"""Lightweight Kafka integration - optional, non-blocking."""

from __future__ import annotations

import json
from typing import Any, Optional

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class KafkaProducer:
    """Thin wrapper around kafka-python producer. Gracefully no-ops if Kafka is unavailable."""

    def __init__(self) -> None:
        self._producer: Any = None
        self._available = False
        self._try_connect()

    def _try_connect(self) -> None:
        if not settings.KAFKA_ENABLED:
            logger.info("Kafka disabled via config")
            return
        try:
            from kafka import KafkaProducer as _KP  # type: ignore[import-untyped]

            self._producer = _KP(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                request_timeout_ms=3000,
                max_block_ms=3000,
            )
            self._available = True
            logger.info("Connected to Kafka at %s", settings.KAFKA_BOOTSTRAP_SERVERS)
        except Exception as e:
            logger.warning("Kafka unavailable – running without event publishing: %s", e)
            self._available = False

    def publish(self, topic: str, key: str, value: dict[str, Any]) -> None:
        """Publish a message. No-op if Kafka is unavailable."""
        if not self._available or self._producer is None:
            return
        try:
            self._producer.send(topic, key=key.encode("utf-8"), value=value)
            self._producer.flush(timeout=2)
        except Exception as e:
            logger.warning("Kafka publish failed: %s", e)

    def publish_transaction_event(self, transaction_data: dict[str, Any]) -> None:
        self.publish("transaction-events", transaction_data.get("transaction_id", ""), transaction_data)

    def publish_fraud_decision(self, decision_data: dict[str, Any]) -> None:
        self.publish("fraud-decisions", decision_data.get("transaction_id", ""), decision_data)

    def close(self) -> None:
        if self._producer:
            try:
                self._producer.close(timeout=3)
            except Exception:
                pass


# Singleton
kafka_producer = KafkaProducer()
