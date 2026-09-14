"""ML engine with XGBoost model and optional ONNX inference."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

FEATURE_NAMES = settings.MODEL_FEATURES


class MLEngine:
    """Loads model and provides risk scoring with feature contributions."""

    def __init__(self) -> None:
        self._xgboost_model: Any = None
        self._onnx_session: Any = None
        self._onnx_available = False
        self._load_models()

    def _load_models(self) -> None:
        """Attempt to load ONNX model, fallback to native XGBoost."""
        # Try ONNX first
        onnx_path = Path(settings.MODEL_PATH)
        if onnx_path.exists():
            try:
                import onnxruntime as ort  # type: ignore[import-untyped]
                self._onnx_session = ort.InferenceSession(str(onnx_path))
                self._onnx_available = True
                logger.info("Loaded ONNX model from %s", onnx_path)
            except Exception as e:
                logger.warning("ONNX load failed: %s", e)
                self._onnx_available = False

        # Fallback to XGBoost
        xgb_path = Path(settings.XGBOOST_MODEL_PATH)
        if xgb_path.exists():
            try:
                import xgboost as xgb
                self._xgboost_model = xgb.XGBClassifier()
                self._xgboost_model.load_model(str(xgb_path))
                logger.info("Loaded XGBoost model from %s", xgb_path)
            except Exception as e:
                logger.warning("XGBoost load failed (will use ONNX or deterministic fallback): %s", e)
        else:
            logger.warning("No model files found at %s or %s", onnx_path, xgb_path)

    @property
    def is_loaded(self) -> bool:
        return self._onnx_available or self._xgboost_model is not None

    def predict_risk(self, features: dict[str, float]) -> dict[str, Any]:
        """Predict fraud risk score and feature contributions."""
        feature_vector = np.array([[features.get(f, 0.0) for f in FEATURE_NAMES]], dtype=np.float32)

        risk_score = 0.5
        contributions = {f: 0.0 for f in FEATURE_NAMES}

        if self._onnx_available and self._onnx_session is not None:
            try:
                input_name = self._onnx_session.get_inputs()[0].name
                result = self._onnx_session.run(None, {input_name: feature_vector})
                # result[0] = class label, result[1] = probabilities [[p_legit, p_fraud]]
                if len(result) > 1:
                    risk_score = float(result[1][0][1])  # fraud probability
                else:
                    risk_score = float(result[0][0])
            except Exception as e:
                logger.error("ONNX inference error: %s", e)

        elif self._xgboost_model is not None:
            try:
                proba = self._xgboost_model.predict_proba(feature_vector)
                risk_score = float(proba[0][1])
                # Use feature importance as approximate contribution
                importances = getattr(self._xgboost_model, "feature_importances_", None)
                if importances is not None:
                    total = float(importances.sum()) or 1.0
                    for i, fname in enumerate(FEATURE_NAMES):
                        contributions[fname] = round(float(importances[i]) / total, 4)
            except Exception as e:
                logger.error("XGBoost inference error: %s", e)

        # Deterministic contribution fallback if model not available
        if not self.is_loaded:
            contributions = self._deterministic_contributions(features)

        return {
            "risk_score": round(min(max(risk_score, 0.0), 1.0), 4),
            "contributions": contributions,
        }

    def _deterministic_contributions(self, features: dict[str, float]) -> dict[str, float]:
        """Fallback feature contribution calculation based on rules."""
        contribs: dict[str, float] = {}

        amount = features.get("amount", 0)
        velocity = features.get("account_velocity_1h", 0)
        speed = features.get("speed_kmh", 0)
        is_new = features.get("is_new_device", 0)

        total = 0.0
        contribs["amount"] = min(amount / 200000, 1.0) * 0.25
        contribs["account_velocity_1h"] = min(velocity / 10, 1.0) * 0.30
        contribs["amount_sum_24h"] = min(amount / 500000, 1.0) * 0.10
        contribs["speed_kmh"] = min(speed / 2000, 1.0) * 0.25
        contribs["is_new_device"] = float(is_new) * 0.10

        total = sum(contribs.values()) or 1.0
        for k in contribs:
            contribs[k] = round(contribs[k] / total, 4)

        return contribs

    def health_check(self) -> str:
        if self._onnx_available:
            return "onnx_loaded"
        if self._xgboost_model is not None:
            return "xgboost_loaded"
        return "unloaded"
