"""
Trains the demand forecasting model: predicts qty_sold_next_day per
store-sku-date from demand_features_daily.csv.

Uses a time-based split (not random) since this is a forecasting
problem — training on the future to predict the past would leak
information, same class of bug as the one fixed in the replenishment
engine.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
import json

DATA_PATH = "demand_features_daily.csv"
MODEL_OUT = "demand_model_xgb_v1.json"
METRICS_OUT = "demand_model_metrics.json"

FEATURE_COLS = [
    "qty_sold_lag_1", "qty_sold_lag_7", "qty_sold_lag_14",
    "rolling_mean_7d", "rolling_mean_14d", "rolling_mean_30d", "rolling_std_7d",
    "days_since_last_sale",
    "day_of_week", "is_weekend", "day_of_month", "month", "is_month_start",
    "promo_active", "shelf_life_days",
]
CATEGORICAL_COLS = ["category"]
TARGET_COL = "qty_sold_next_day"


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["txn_date"] = pd.to_datetime(df["txn_date"])
    for c in ["is_weekend", "is_month_start", "promo_active"]:
        df[c] = df[c].astype(int)
    df = pd.get_dummies(df, columns=CATEGORICAL_COLS, prefix="cat")
    return df


def wape(y_true, y_pred):
    """Weighted Absolute Percentage Error — standard metric for demand
    forecasting since plain MAPE blows up on low/zero-sale days."""
    return np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true))


def main():
    df = pd.read_csv(DATA_PATH)
    df = prepare(df)

    cat_dummy_cols = [c for c in df.columns if c.startswith("cat_")]
    feature_cols = FEATURE_COLS + cat_dummy_cols

    # time-based split: last 21 days held out per store-sku for validation
    cutoff_date = df["txn_date"].max() - pd.Timedelta(days=21)
    train = df[df["txn_date"] <= cutoff_date]
    valid = df[df["txn_date"] > cutoff_date]

    X_train, y_train = train[feature_cols], train[TARGET_COL]
    X_valid, y_valid = valid[feature_cols], valid[TARGET_COL]

    model = xgb.XGBRegressor(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
        early_stopping_rounds=30,
        eval_metric="mae",
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_valid, y_valid)],
        verbose=False,
    )

    preds = model.predict(X_valid)
    preds = np.clip(preds, 0, None)  # demand can't be negative

    metrics = {
        "mae": float(mean_absolute_error(y_valid, preds)),
        "rmse": float(np.sqrt(mean_squared_error(y_valid, preds))),
        "wape": float(wape(y_valid.values, preds)),
        "n_train": int(len(train)),
        "n_valid": int(len(valid)),
        "cutoff_date": str(cutoff_date.date()),
        "feature_cols": feature_cols,
    }

    model.save_model(MODEL_OUT)
    with open(METRICS_OUT, "w") as f:
        json.dump(metrics, f, indent=2)

    print(json.dumps(metrics, indent=2))

    top_features = sorted(
        zip(feature_cols, model.feature_importances_),
        key=lambda x: -x[1]
    )[:8]
    print("\nTop features:")
    for name, imp in top_features:
        print(f"  {name}: {imp:.4f}")


if __name__ == "__main__":
    main()
