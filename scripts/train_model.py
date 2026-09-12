"""Train a lightweight XGBoost fraud detection model on synthetic data."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def generate_synthetic_data(n_samples: int = 10000, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic fraud transaction data with realistic feature correlations.

    Fraudulent transactions exhibit combinations of:
    - High velocity
    - Large amounts
    - New devices
    - Impossible travel speeds
    - Suspicious connections
    """
    rng = np.random.default_rng(seed)

    records = []
    for _ in range(n_samples):
        is_fraud = rng.random() < 0.08  # ~8% fraud rate

        if is_fraud:
            # Fraudulent patterns
            velocity = int(rng.poisson(lam=6) + rng.integers(2, 8))
            amount = float(rng.lognormal(mean=11.5, sigma=0.8))  # ~₹100k
            speed = float(rng.choice([0, 0, 0, 850, 1200, 1500, 2500], p=[0.2, 0.2, 0.15, 0.15, 0.15, 0.1, 0.05]))
            is_new_device = bool(rng.random() < 0.7)
            amount_24h = amount * rng.uniform(1.5, 5.0)
            graph_risk = float(rng.choice([0, 60, 70, 80, 100], p=[0.15, 0.15, 0.2, 0.3, 0.2]))
        else:
            # Normal patterns
            velocity = int(rng.poisson(lam=1.5))
            amount = float(rng.lognormal(mean=8.5, sigma=1.0))  # ~₹5k
            speed = float(rng.uniform(0, 200))
            is_new_device = bool(rng.random() < 0.1)
            amount_24h = amount * rng.uniform(1.0, 2.0)
            graph_risk = float(rng.choice([0, 0, 0, 0, 60], p=[0.6, 0.2, 0.1, 0.05, 0.05]))

        records.append({
            "amount": round(amount, 2),
            "account_velocity_1h": max(0, velocity),
            "amount_sum_24h": round(amount_24h, 2),
            "speed_kmh": round(speed, 2),
            "is_new_device": int(is_new_device),
            "graph_penalty": graph_risk,
            "label": int(is_fraud),
        })

    return pd.DataFrame(records)


def train() -> None:
    """Train and evaluate the XGBoost model."""
    print("Generating synthetic training data...")
    df = generate_synthetic_data(n_samples=15000)

    features = ["amount", "account_velocity_1h", "amount_sum_24h", "speed_kmh", "is_new_device"]
    X = df[features].values
    y = np.asarray(df["label"].values)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training set: {len(X_train)} samples ({y_train.sum()} fraud)")
    print(f"Test set:     {len(X_test)} samples ({y_test.sum()} fraud)")

    import xgboost as xgb

    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=float((y_train == 0).sum() / max((y_train == 1).sum(), 1)),
        eval_metric="aucpr",
        random_state=42,
        use_label_encoder=False,
    )

    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # Evaluate
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("\n--- Classification Report ---")
    print(classification_report(y_test, y_pred, target_names=["Legit", "Fraud"]))

    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary")
    auc = roc_auc_score(y_test, y_proba)
    print(f"ROC-AUC: {auc:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1:        {f1:.4f}")

    # Save XGBoost model
    model_dir = PROJECT_ROOT / "models"
    model_dir.mkdir(exist_ok=True)

    xgb_path = model_dir / "fraud_model.pkl"
    model.save_model(str(xgb_path))
    print(f"\nXGBoost model saved to {xgb_path}")

    # Export to ONNX via onnxmltools (XGBoost native)
    try:
        from onnxmltools import convert_xgboost  # type: ignore[import-untyped]
        from onnxmltools.convert.common.data_types import FloatTensorType  # type: ignore[import-untyped]

        initial_type = [("float_input", FloatTensorType([None, len(features)]))]
        onnx_model = convert_xgboost(model, initial_types=initial_type)
        onnx_path = model_dir / "fraud_model.onnx"
        with open(onnx_path, "wb") as f:
            f.write(onnx_model.SerializeToString())
        print(f"ONNX model saved to {onnx_path}")
    except ImportError:
        print("onnxmltools not installed — skipping ONNX export (XGBoost model available)")
    except Exception as e:
        print(f"ONNX export failed (XGBoost native model still available): {e}")

    print("\nTraining complete.")


if __name__ == "__main__":
    train()
