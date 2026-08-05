"""
Translates demand forecasts into reorder recommendations per store-SKU.

Inputs:
  - outputs/demand_forecast_output.csv   (predicted_qty from the trained model)
  - data/demand_features_daily.csv       (rolling_std_7d, as a demand-
                                           variability proxy for safety stock)
  - data/inventory_snapshots_synthetic.csv (current stock_on_hand, stock_in_transit)
  - data/supplier_lead_times_synthetic.csv (lead_time_days, lead_time_variance)

Output:
  - outputs/replenishment_recommendations.csv

Formula (standard safety-stock-under-demand-and-lead-time-uncertainty):
    safety_stock = Z * sqrt(
        lead_time_days * demand_std^2
        + avg_daily_demand^2 * lead_time_variance^2
    )
    reorder_point = avg_daily_demand * lead_time_days + safety_stock
    order_up_to    = avg_daily_demand * (lead_time_days + review_period_days) + safety_stock
    projected_position = stock_on_hand + stock_in_transit

Z is the service-level factor (Z=1.65 -> ~95% service level).
A SKU is flagged 'urgent' when projected_position is already below the
reorder point AND there's no stock in transit to cover the gap before
the supplier lead time elapses.
"""
import pandas as pd
import numpy as np

FORECAST_PATH = "demand_forecast_output.csv"
FEATURES_PATH = "demand_features_daily.csv"
INVENTORY_PATH = "inventory_snapshots_synthetic.csv"
LEAD_TIME_PATH = "supplier_lead_times_synthetic.csv"
OUT_PATH = "replenishment_recommendations.csv"

SERVICE_LEVEL_Z = 1.65   # ~95% service level
REVIEW_PERIOD_DAYS = 7   # how often replenishment decisions are reviewed


def load_inputs():
    forecast = pd.read_csv(FORECAST_PATH, parse_dates=["forecast_date"])
    features = pd.read_csv(FEATURES_PATH, parse_dates=["txn_date"])
    inventory = pd.read_csv(INVENTORY_PATH, parse_dates=["snapshot_date"])
    lead_times = pd.read_csv(LEAD_TIME_PATH)
    return forecast, features, inventory, lead_times


def get_latest_demand_std(features: pd.DataFrame) -> pd.DataFrame:
    """Most recent rolling_std_7d per store-sku, used as the demand
    variability input to the safety stock formula."""
    latest = features.sort_values("txn_date").groupby(["store_id", "sku_id"]).tail(1)
    return latest[["store_id", "sku_id", "rolling_std_7d"]].rename(
        columns={"rolling_std_7d": "demand_std"}
    )


def get_latest_inventory(inventory: pd.DataFrame) -> pd.DataFrame:
    latest = inventory.sort_values("snapshot_date").groupby(["store_id", "sku_id"]).tail(1)
    return latest[["store_id", "sku_id", "stock_on_hand", "stock_in_transit"]]


def compute_recommendations(forecast, demand_std, inventory, lead_times) -> pd.DataFrame:
    df = forecast.merge(demand_std, on=["store_id", "sku_id"], how="left")
    df = df.merge(inventory, on=["store_id", "sku_id"], how="left")
    df = df.merge(lead_times, on=["store_id", "sku_id"], how="left")

    df["demand_std"] = df["demand_std"].fillna(df["predicted_qty"] * 0.3)  # fallback if no history
    df["avg_daily_demand"] = df["predicted_qty"]

    df["safety_stock"] = SERVICE_LEVEL_Z * np.sqrt(
        df["lead_time_days"] * df["demand_std"] ** 2
        + (df["avg_daily_demand"] ** 2) * (df["lead_time_variance"] ** 2)
    )

    df["reorder_point"] = df["avg_daily_demand"] * df["lead_time_days"] + df["safety_stock"]
    df["order_up_to_level"] = (
        df["avg_daily_demand"] * (df["lead_time_days"] + REVIEW_PERIOD_DAYS) + df["safety_stock"]
    )

    df["projected_position"] = df["stock_on_hand"] + df["stock_in_transit"]

    df["below_reorder_point"] = df["projected_position"] < df["reorder_point"]

    # urgent: projected position won't last through the supplier lead
    # time window at the current demand rate (i.e. stockout is imminent,
    # not just "time to plan a reorder")
    df["days_of_cover"] = df["projected_position"] / df["avg_daily_demand"].replace(0, np.nan)
    df["urgent"] = df["below_reorder_point"] & (df["days_of_cover"] < df["lead_time_days"])

    df["recommended_order_qty"] = np.where(
        df["below_reorder_point"],
        np.maximum(df["order_up_to_level"] - df["projected_position"], 0),
        0,
    )

    cols = [
        "store_id", "sku_id", "forecast_date", "avg_daily_demand", "demand_std",
        "lead_time_days", "lead_time_variance", "stock_on_hand", "stock_in_transit",
        "projected_position", "safety_stock", "reorder_point", "order_up_to_level",
        "days_of_cover", "below_reorder_point", "urgent", "recommended_order_qty",
    ]
    result = df[cols].copy()
    for c in ["avg_daily_demand", "demand_std", "safety_stock", "reorder_point",
              "order_up_to_level", "days_of_cover", "recommended_order_qty"]:
        result[c] = result[c].round(1)
    return result


def main():
    forecast, features, inventory, lead_times = load_inputs()
    demand_std = get_latest_demand_std(features)
    latest_inventory = get_latest_inventory(inventory)

    recs = compute_recommendations(forecast, demand_std, latest_inventory, lead_times)
    recs = recs.sort_values(["urgent", "below_reorder_point"], ascending=False)
    recs.to_csv(OUT_PATH, index=False)

    print(f"Wrote {len(recs)} recommendations to {OUT_PATH}")
    print(f"  Below reorder point: {recs['below_reorder_point'].sum()}")
    print(f"  Urgent: {recs['urgent'].sum()}")
    print()
    print(recs[["store_id", "sku_id", "projected_position", "reorder_point",
                 "urgent", "recommended_order_qty"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
