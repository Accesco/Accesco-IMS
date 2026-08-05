"""
Flags unusual inventory activity across three complementary checks:

1. Sales volume anomalies (rolling z-score): today's qty_sold vs a
   rolling baseline built ONLY from prior days (no leakage) — catches
   sudden spikes (bulk orders, data entry errors) and drops (stockouts
   not reflected elsewhere, system outages).
2. Inventory discrepancy: expected day-over-day stock change (from
   recorded sales) vs the actual change in stock_on_hand — a mismatch
   means stock moved without a matching transaction (shrinkage, theft,
   miscount).
3. Multivariate outliers (Isolation Forest): catches combinations that
   look normal on any single axis but unusual jointly.

Run against *_with_anomalies.csv (from inject_synthetic_anomalies.py)
by default for validation; point at the real synthetic/live files by
changing SALES_PATH / INVENTORY_PATH for production use.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

SALES_PATH = "sales_transactions_with_anomalies.csv"
INVENTORY_PATH = "inventory_snapshots_with_anomalies.csv"
GROUND_TRUTH_PATH = "anomaly_ground_truth.csv"
OUT_PATH = "anomaly_flags.csv"

Z_THRESHOLD = 3.0
ROLLING_WINDOW = 14


def build_dense_sales_panel(sales: pd.DataFrame) -> pd.DataFrame:
    sales["txn_date"] = pd.to_datetime(sales["txn_date"])
    all_dates = pd.date_range(sales["txn_date"].min(), sales["txn_date"].max(), freq="D")
    pairs = sales[["store_id", "sku_id"]].drop_duplicates()
    panel = pairs.assign(key=1).merge(
        pd.DataFrame({"txn_date": all_dates, "key": 1}), on="key"
    ).drop(columns="key")
    daily = sales.groupby(["store_id", "sku_id", "txn_date"], as_index=False).agg(
        qty_sold=("qty_sold", "sum"), promo_active=("promo_flag", "max")
    )
    panel = panel.merge(daily, on=["store_id", "sku_id", "txn_date"], how="left")
    panel["qty_sold"] = panel["qty_sold"].fillna(0)
    panel["promo_active"] = panel["promo_active"].fillna(False)
    return panel.sort_values(["store_id", "sku_id", "txn_date"])


def detect_sales_zscore_anomalies(panel: pd.DataFrame) -> pd.DataFrame:
    grp = panel.groupby(["store_id", "sku_id"])["qty_sold"]
    # baseline built from PRIOR days only (shift before rolling) so
    # today's value can't inflate its own baseline
    panel["roll_mean"] = grp.transform(lambda s: s.shift(1).rolling(ROLLING_WINDOW, min_periods=5).mean())
    panel["roll_std"] = grp.transform(lambda s: s.shift(1).rolling(ROLLING_WINDOW, min_periods=5).std())
    panel["z_score"] = (panel["qty_sold"] - panel["roll_mean"]) / panel["roll_std"].replace(0, np.nan)

    flagged = panel[panel["z_score"].abs() >= Z_THRESHOLD].copy()
    # a promo-day spike is expected, not unusual — don't surface it as an
    # anomaly requiring investigation (unexplained drops on promo days
    # still matter, so only spikes are suppressed)
    explained_by_promo = flagged["promo_active"] & (flagged["z_score"] > 0)
    flagged = flagged[~explained_by_promo].copy()

    flagged["anomaly_type"] = np.where(flagged["z_score"] > 0, "sales_spike", "sales_drop")
    flagged["severity"] = flagged["z_score"].abs().round(2)
    return flagged[["store_id", "sku_id", "txn_date", "qty_sold", "roll_mean",
                     "z_score", "anomaly_type", "severity"]].rename(columns={"txn_date": "date"})


def detect_inventory_discrepancies(inventory: pd.DataFrame, sales_panel: pd.DataFrame) -> pd.DataFrame:
    inv = inventory.copy()
    inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"])
    inv = inv.sort_values(["store_id", "sku_id", "snapshot_date"])

    grp = inv.groupby(["store_id", "sku_id"])
    inv["prior_stock"] = grp["stock_on_hand"].shift(1)
    inv["actual_change"] = inv["stock_on_hand"] - inv["prior_stock"]
    inv["arrivals"] = grp["stock_in_transit"].shift(1).fillna(0) - inv["stock_in_transit"].fillna(0)
    inv["arrivals"] = inv["arrivals"].clip(lower=0)  # in-transit only decreases on arrival, ignore noise

    sales_lookup = sales_panel.rename(columns={"txn_date": "snapshot_date"})[
        ["store_id", "sku_id", "snapshot_date", "qty_sold"]
    ]
    inv = inv.merge(sales_lookup, on=["store_id", "sku_id", "snapshot_date"], how="left")
    inv["qty_sold"] = inv["qty_sold"].fillna(0)

    inv["expected_change"] = inv["arrivals"] - inv["qty_sold"]
    inv["discrepancy"] = inv["actual_change"] - inv["expected_change"]

    # flag discrepancies that are large relative to typical daily sales
    # for that SKU (a 2-unit gap on a slow SKU matters more than on a
    # fast one) — use a simple absolute floor plus a relative check
    typical_daily = inv.groupby(["store_id", "sku_id"])["qty_sold"].transform("mean").clip(lower=1)
    flagged = inv[inv["discrepancy"].abs() > (typical_daily * 3).clip(lower=5)].copy()
    flagged["anomaly_type"] = "inventory_discrepancy"
    flagged["severity"] = flagged["discrepancy"].abs().round(1)
    return flagged[["store_id", "sku_id", "snapshot_date", "discrepancy",
                     "anomaly_type", "severity"]].rename(columns={"snapshot_date": "date"})


def detect_multivariate_outliers(panel: pd.DataFrame) -> pd.DataFrame:
    features = panel.dropna(subset=["roll_mean", "roll_std"]).copy()
    if features.empty:
        return pd.DataFrame(columns=["store_id", "sku_id", "date", "anomaly_type", "severity"])

    X = features[["qty_sold", "roll_mean", "roll_std"]].fillna(0)
    model = IsolationForest(contamination=0.02, random_state=42)
    model.fit(X)
    features["is_outlier"] = model.predict(X) == -1
    features["anomaly_score"] = -model.decision_function(X)  # higher = more anomalous

    flagged = features[features["is_outlier"]].copy()
    flagged["anomaly_type"] = "multivariate_outlier"
    flagged["severity"] = flagged["anomaly_score"].round(3)
    return flagged[["store_id", "sku_id", "txn_date", "anomaly_type", "severity"]].rename(
        columns={"txn_date": "date"}
    )


def main():
    sales = pd.read_csv(SALES_PATH)
    inventory = pd.read_csv(INVENTORY_PATH)

    panel = build_dense_sales_panel(sales)

    zscore_flags = detect_sales_zscore_anomalies(panel)
    inventory_flags = detect_inventory_discrepancies(inventory, panel)
    multivariate_flags = detect_multivariate_outliers(panel)

    all_flags = pd.concat([
        zscore_flags[["store_id", "sku_id", "date", "anomaly_type", "severity"]],
        inventory_flags[["store_id", "sku_id", "date", "anomaly_type", "severity"]],
        multivariate_flags[["store_id", "sku_id", "date", "anomaly_type", "severity"]],
    ], ignore_index=True)
    all_flags["date"] = pd.to_datetime(all_flags["date"]).dt.date
    all_flags = all_flags.sort_values("severity", ascending=False)
    all_flags.to_csv(OUT_PATH, index=False)

    print(f"Total flags: {len(all_flags)}")
    print(all_flags["anomaly_type"].value_counts())
    print()

    # validate against known injected anomalies, if present
    try:
        ground_truth = pd.read_csv(GROUND_TRUTH_PATH, parse_dates=["date"])
        ground_truth["date"] = ground_truth["date"].dt.date
        print("Validation against injected ground truth:")
        for _, g in ground_truth.iterrows():
            match = all_flags[
                (all_flags.store_id == g.store_id) & (all_flags.sku_id == g.sku_id)
                & (all_flags.date == g.date)
            ]
            caught = not match.empty
            print(f"  {g.type} @ {g.store_id}/{g.sku_id}/{g.date}: "
                  f"{'CAUGHT (' + match.iloc[0].anomaly_type + ')' if caught else 'MISSED'}")
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    main()
