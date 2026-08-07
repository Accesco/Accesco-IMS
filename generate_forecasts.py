"""
Inference script: loads the trained XGBoost demand model, predicts 
next-day quantities using the latest available features from 
demand_features_daily.csv, and saves to demand_forecast_output.csv.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import json
from datetime import datetime

FEATURES_PATH = "demand_features_daily.csv"
MODEL_PATH = "demand_model_xgb_v1.json"
METRICS_PATH = "demand_model_metrics.json"
OUT_PATH = "demand_forecast_output.csv"

def main():
    # 1. Load data and model
    df = pd.read_csv(FEATURES_PATH)
    df["txn_date"] = pd.to_datetime(df["txn_date"])
    
    model = xgb.XGBRegressor()
    model.load_model(MODEL_PATH)
    
    with open(METRICS_PATH, "r") as f:
        metrics = json.load(f)
    feature_cols = metrics["feature_cols"]
    
    # 2. Prepare features matching training format
    prep_df = df.copy()
    for c in ["is_weekend", "is_month_start", "promo_active"]:
        if c in prep_df.columns:
            prep_df[c] = prep_df[c].astype(int)
    prep_df = pd.get_dummies(prep_df, columns=["category"], prefix="cat")
    
    for col in feature_cols:
        if col not in prep_df.columns:
            prep_df[col] = 0
            
    # 3. Filter for the latest available date per store-sku
    latest_dates = prep_df.groupby(["store_id", "sku_id"])["txn_date"].transform("max")
    latest_rows = prep_df[prep_df["txn_date"] == latest_dates].copy()
    
    # 4. Predict demand
    X = latest_rows[feature_cols]
    preds = model.predict(X)
    latest_rows["predicted_qty"] = np.clip(preds, 0, None)  # Demand can't be negative[cite: 6]
    
    # 5. Format output matching schema (demand_forecast_output)[cite: 1]
    latest_rows["forecast_date"] = latest_rows["txn_date"] + pd.Timedelta(days=1)
    latest_rows["forecast_generated_at"] = datetime.now().isoformat()
    latest_rows["model_version"] = "xgb-demand-v1"
    
    output_df = latest_rows[[
        "store_id", "sku_id", "forecast_date", 
        "forecast_generated_at", "predicted_qty", "model_version"
    ]]
    
    # 6. Save to CSV
    output_df.to_csv(OUT_PATH, index=False)
    print(f"Generated {len(output_df)} forecast rows. Saved to {OUT_PATH}")
    print(output_df.head())

if __name__ == "__main__":
    main()