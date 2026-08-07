"""
Generates synthetic sales_transactions data consistent with
demand_forecast_schema.sql, for building/testing the pipeline before
real data access is wired up.

Mirrors the store setup used in the replenishment engine
(DS-BLR-01/02/03) and a small representative SKU catalog.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

STORES = ["DS-BLR-01", "DS-BLR-02", "DS-BLR-03"]

SKUS = [
    {"sku_id": "SKU-MILK-500", "category": "dairy", "base_rate": 40, "shelf_life_days": 3},
    {"sku_id": "SKU-BREAD-400", "category": "bakery", "base_rate": 25, "shelf_life_days": 2},
    {"sku_id": "SKU-EGG-6PK", "category": "dairy", "base_rate": 30, "shelf_life_days": 14},
    {"sku_id": "SKU-RICE-1KG", "category": "staples", "base_rate": 15, "shelf_life_days": 365},
    {"sku_id": "SKU-CHIPS-100", "category": "snacks", "base_rate": 20, "shelf_life_days": 120},
    {"sku_id": "SKU-COLA-750", "category": "beverages", "base_rate": 18, "shelf_life_days": 180},
    {"sku_id": "SKU-DETERGENT-1L", "category": "household", "base_rate": 8, "shelf_life_days": 720},
    {"sku_id": "SKU-BANANA-1KG", "category": "produce", "base_rate": 22, "shelf_life_days": 5},
]

N_DAYS = 180
START_DATE = datetime(2026, 1, 1)


def simulate_daily_qty(base_rate, day_idx, store_multiplier):
    dow = (START_DATE + timedelta(days=day_idx)).weekday()
    weekend_boost = 1.35 if dow >= 5 else 1.0
    trend = 1.0 + 0.0008 * day_idx  # slow organic growth
    promo = np.random.rand() < 0.05
    promo_boost = 1.8 if promo else 1.0
    lam = base_rate * store_multiplier * weekend_boost * trend * promo_boost
    qty = np.random.poisson(lam=max(lam, 0.1))
    return qty, promo


def main():
    rows = []
    store_multipliers = {"DS-BLR-01": 1.15, "DS-BLR-02": 0.9, "DS-BLR-03": 1.0}

    for store_id in STORES:
        mult = store_multipliers[store_id]
        for sku in SKUS:
            for day_idx in range(N_DAYS):
                date = START_DATE + timedelta(days=day_idx)
                qty, promo = simulate_daily_qty(sku["base_rate"], day_idx, mult)
                if qty == 0:
                    continue  # no transaction rows on zero-sale days (realistic)
                rows.append({
                    "store_id": store_id,
                    "sku_id": sku["sku_id"],
                    "category": sku["category"],
                    "shelf_life_days": sku["shelf_life_days"],
                    "txn_date": date.date().isoformat(),
                    "qty_sold": qty,
                    "promo_flag": promo,
                })

    df = pd.DataFrame(rows)
    out_path = "sales_transactions_synthetic.csv"
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df)} rows across {len(STORES)} stores x {len(SKUS)} SKUs x {N_DAYS} days")
    print(df.head())


if __name__ == "__main__":
    main()
