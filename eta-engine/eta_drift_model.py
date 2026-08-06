"""
eta_drift_model.py
-------------------
Trains a model to predict ETA "drift" -- the gap between a naive ETA
(distance_remaining / current_speed) and the actual remaining time --
using only information a real telemetry stream would provide at that
moment: lane, carrier, time of day, current speed, distance covered so
far. This matches the blueprint's Tracking Layer concept ("ML ETA
Drift") much more directly than just re-deriving the naive formula.

Final corrected ETA = naive_eta_remaining_min + predicted_drift_min.

Evaluated against the naive baseline on a held-out set of *entire
shipments* (not individual ticks) -- a shipment's ticks are highly
correlated, so splitting by shipment_id avoids leaking a truck's own
trip across train/test.

Usage:
    python eta_drift_model.py --data fleet_telemetry.csv
"""

import argparse
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CATEGORICAL_FEATURES = ["lane_id", "carrier_id"]
NUMERIC_FEATURES = [
    "carrier_on_time_score",
    "hour_of_day",
    "is_rush_hour",
    "distance_remaining_km",
    "progress_fraction",
    "current_speed_kmh",
    "avg_speed_so_far_kmh",
]
TARGET = "drift_min"


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("num", "passthrough", NUMERIC_FEATURES),
        ]
    )
    model = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
    )
    return Pipeline([("preprocess", preprocessor), ("model", model)])


def train_and_evaluate(df: pd.DataFrame, seed: int = 42):
    X = df[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
    y = df[TARGET]
    groups = df["shipment_id"]

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    test_df = df.iloc[test_idx]

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    pred_drift = pipeline.predict(X_test)
    corrected_eta_remaining = test_df["naive_eta_remaining_min"].values + pred_drift
    actual_remaining = test_df["actual_remaining_min"].values
    naive_remaining = test_df["naive_eta_remaining_min"].values

    naive_mae = mean_absolute_error(actual_remaining, naive_remaining)
    naive_rmse = mean_squared_error(actual_remaining, naive_remaining) ** 0.5

    corrected_mae = mean_absolute_error(actual_remaining, corrected_eta_remaining)
    corrected_rmse = mean_squared_error(actual_remaining, corrected_eta_remaining) ** 0.5

    n_train_shipments = df.iloc[train_idx]["shipment_id"].nunique()
    n_test_shipments = test_df["shipment_id"].nunique()

    metrics = {
        "n_train_ticks": int(len(X_train)),
        "n_test_ticks": int(len(X_test)),
        "n_train_shipments": int(n_train_shipments),
        "n_test_shipments": int(n_test_shipments),
        "naive_mae_min": round(float(naive_mae), 3),
        "naive_rmse_min": round(float(naive_rmse), 3),
        "model_corrected_mae_min": round(float(corrected_mae), 3),
        "model_corrected_rmse_min": round(float(corrected_rmse), 3),
        "mae_improvement_pct": round(100.0 * (naive_mae - corrected_mae) / naive_mae, 2),
        "rmse_improvement_pct": round(100.0 * (naive_rmse - corrected_rmse) / naive_rmse, 2),
    }
    return pipeline, metrics


def main():
    parser = argparse.ArgumentParser(description="Train the ETA drift correction model")
    parser.add_argument("--data", default="fleet_telemetry.csv")
    parser.add_argument("--model-out", default="eta_drift_model.joblib")
    parser.add_argument("--metrics-out", default="eta_drift_metrics.json")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    pipeline, metrics = train_and_evaluate(df, seed=args.seed)

    joblib.dump(pipeline, args.model_out)
    with open(args.metrics_out, "w") as f:
        json.dump(metrics, f, indent=2)

    print(json.dumps(metrics, indent=2))
    print(f"\nModel saved to: {args.model_out}")


if __name__ == "__main__":
    main()
