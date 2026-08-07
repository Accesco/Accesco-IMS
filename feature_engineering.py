"""
Builds the demand_features_daily feature set (see
schema/demand_forecast_schema.sql) from raw sales_transactions.

Input:  data/sales_transactions_synthetic.csv (store_id, sku_id, txn_date,
        qty_sold, promo_flag, category, shelf_life_days)
Output: data/demand_features_daily.csv

Swap the CSV read for a real sales_transactions query when wiring this
into the actual pipeline — the feature logic itself doesn't change.
"""
import pandas as pd
import numpy as np

IN_PATH = "sales_transactions_synthetic.csv"
OUT_PATH = "demand_features_daily.csv"

def build_daily_panel(txns: pd.DataFrame) -> pd.DataFrame:
    """Turn sparse transaction rows into a dense store-sku-date panel
    (every day present, qty_sold = 0 where there was no sale)."""
    txns["txn_date"] = pd.to_datetime(txns["txn_date"])

    all_dates = pd.date_range(txns["txn_date"].min(), txns["txn_date"].max(), freq="D")
    store_sku = txns[["store_id", "sku_id", "category", "shelf_life_days"]].drop_duplicates()

    panel = (
        store_sku.assign(key=1)
        .merge(pd.DataFrame({"txn_date": all_dates, "key": 1}), on="key")
        .drop(columns="key")
    )

    daily_sales = (
        txns.groupby(["store_id", "sku_id", "txn_date"], as_index=False)
        .agg(qty_sold=("qty_sold", "sum"), promo_active=("promo_flag", "max"))
    )

    panel = panel.merge(daily_sales, on=["store_id", "sku_id", "txn_date"], how="left")
    panel["qty_sold"] = panel["qty_sold"].fillna(0).astype(int)
    panel["promo_active"] = panel["promo_active"].fillna(False)
    return panel


def add_features(panel: pd.DataFrame) -> pd.DataFrame:
    panel = panel.sort_values(["store_id", "sku_id", "txn_date"]).reset_index(drop=True)
    grp = panel.groupby(["store_id", "sku_id"])["qty_sold"]

    panel["qty_sold_lag_1"] = grp.shift(1)
    panel["qty_sold_lag_7"] = grp.shift(7)
    panel["qty_sold_lag_14"] = grp.shift(14)

    panel["rolling_mean_7d"] = grp.transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
    panel["rolling_mean_14d"] = grp.transform(lambda s: s.shift(1).rolling(14, min_periods=1).mean())
    panel["rolling_mean_30d"] = grp.transform(lambda s: s.shift(1).rolling(30, min_periods=1).mean())
    panel["rolling_std_7d"] = grp.transform(lambda s: s.shift(1).rolling(7, min_periods=2).std())

    # days since last actual sale (>0 qty)
    def days_since_last_sale(s):
        had_sale = (s > 0).astype(int)
        out = np.zeros(len(s))
        counter = np.nan
        for i, v in enumerate(had_sale):
            out[i] = counter if not np.isnan(counter) else np.nan
            counter = 0 if v == 1 else (counter + 1 if not np.isnan(counter) else np.nan)
        return pd.Series(out, index=s.index)

    panel["days_since_last_sale"] = grp.transform(days_since_last_sale)

    panel["day_of_week"] = panel["txn_date"].dt.dayofweek
    panel["is_weekend"] = panel["day_of_week"] >= 5
    panel["day_of_month"] = panel["txn_date"].dt.day
    panel["month"] = panel["txn_date"].dt.month
    panel["is_month_start"] = panel["txn_date"].dt.is_month_start

    # target: next day's qty sold (what the model will predict)
    panel["qty_sold_next_day"] = grp.shift(-1)

    return panel


def main():
    txns = pd.read_csv(IN_PATH)
    panel = build_daily_panel(txns)
    features = add_features(panel)

    # drop rows without enough history to have lag_14, and rows without a
    # next-day target (last day per store-sku, can't train on it)
    features = features.dropna(subset=["qty_sold_lag_14", "qty_sold_next_day"])

    features.to_csv(OUT_PATH, index=False)
    print(f"Feature table: {features.shape[0]} rows, {features.shape[1]} columns")
    print(f"Saved to {OUT_PATH}")
    print(features.columns.tolist())


if __name__ == "__main__":
    main()
