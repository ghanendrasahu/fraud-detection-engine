"""Logging configuration with transaction-aware context."""

from __future__ import annotations

import logging
import sys
from typing import Any

from app.config import settings


class TransactionFilter(logging.Filter):
    """Injects default transaction_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "transaction_id"):
            record.transaction_id = "N/A"
        return True


class TransactionLogger(logging.LoggerAdapter):
    """Logger adapter that prepends transaction_id to messages."""

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        txn_id = self.extra.get("transaction_id", "N/A")  # type: ignore[union-attr]
        return f"transaction_id={txn_id} {msg}", kwargs


def setup_logging() -> None:
    """Configure application logging."""
    log_format = (
        "%(asctime)s %(levelname)-8s %(name)-20s %(message)s"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.addFilter(TransactionFilter())


def get_logger(name: str, transaction_id: str | None = None) -> logging.LoggerAdapter:
    """Get a logger with optional transaction context."""
    base = logging.getLogger(name)
    extra = {"transaction_id": transaction_id or "N/A"}
    return TransactionLogger(base, extra)
