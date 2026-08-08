"""
maintenance_model.py
----------------------
Trains a model to predict maintenance "drift" -- the gap between a
naive fixed-interval estimate ("every 10,000 km") and the actual
remaining distance until service is genuinely needed, using usage-
pattern signals: load, driving harshness, terrain, vehicle age.

Final corrected estimate = naive_km_remaining + predicted_drift_km.

Evaluated on held-out *vehicles* (not held-out rows) -- one vehicle's
snapshots are highly correlated (same driving style, same lane), so
row-level splitting would leak a vehicle's own pattern across
train/test, the same reasoning as the ETA model's shipment-level split.

Usage:
    python maintenance_model.py --data vehicle_usage.csv
"""

import argparse
import json

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CATEGORICAL_FEATURES = ["lane_id"]
NUMERIC_FEATURES = [
    "terrain_factor",
    "vehicle_age_years",
    "km_since_last_service",
    "days_since_last_service",
    "avg_daily_km_this_interval",
    "avg_load_utilization_pct",
    "harsh_events_per_1000km",
]
TARGET = "drift_km"


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
    groups = df["vehicle_id"]

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    test_df = df.iloc[test_idx]

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    pred_drift = pipeline.predict(X_test)
    corrected_remaining = test_df["naive_km_remaining"].values + pred_drift
    actual_remaining = test_df["actual_km_remaining"].values
    naive_remaining = test_df["naive_km_remaining"].values

    naive_mae = mean_absolute_error(actual_remaining, naive_remaining)
    naive_rmse = mean_squared_error(actual_remaining, naive_remaining) ** 0.5
    corrected_mae = mean_absolute_error(actual_remaining, corrected_remaining)
    corrected_rmse = mean_squared_error(actual_remaining, corrected_remaining) ** 0.5

    metrics = {
        "n_train_snapshots": int(len(X_train)),
        "n_test_snapshots": int(len(X_test)),
        "n_train_vehicles": int(df.iloc[train_idx]["vehicle_id"].nunique()),
        "n_test_vehicles": int(test_df["vehicle_id"].nunique()),
        "naive_mae_km": round(float(naive_mae), 1),
        "naive_rmse_km": round(float(naive_rmse), 1),
        "model_corrected_mae_km": round(float(corrected_mae), 1),
        "model_corrected_rmse_km": round(float(corrected_rmse), 1),
        "mae_improvement_pct": round(100.0 * (naive_mae - corrected_mae) / naive_mae, 2),
        "rmse_improvement_pct": round(100.0 * (naive_rmse - corrected_rmse) / naive_rmse, 2),
    }
    return pipeline, metrics


def main():
    parser = argparse.ArgumentParser(description="Train the maintenance drift correction model")
    parser.add_argument("--data", default="vehicle_usage.csv")
    parser.add_argument("--model-out", default="maintenance_drift_model.joblib")
    parser.add_argument("--metrics-out", default="maintenance_drift_metrics.json")
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
