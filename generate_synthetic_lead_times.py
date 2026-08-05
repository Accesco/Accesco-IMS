"""
Generates synthetic supplier_lead_times data consistent with
demand_forecast_schema.sql — one supplier per store-SKU pair, with a
mean lead time and variance the replenishment engine uses for safety
stock calculations.
"""
import numpy as np
import pandas as pd

np.random.seed(11)

SALES_PATH = "sales_transactions_synthetic.csv"
OUT_PATH = "supplier_lead_times_synthetic.csv"

# base lead time varies by category — perishables sourced locally/faster,
# packaged goods from farther/less frequent supply runs
CATEGORY_LEAD_TIME = {
    "dairy": 1.5, "produce": 1.5, "bakery": 1.0,
    "beverages": 3.0, "snacks": 3.0, "staples": 4.0, "household": 5.0,
}


def main():
    sales = pd.read_csv(SALES_PATH)
    pairs = sales[["store_id", "sku_id", "category"]].drop_duplicates()

    rows = []
    for _, r in pairs.iterrows():
        base = CATEGORY_LEAD_TIME.get(r["category"], 3.0)
        lead_time = max(base + np.random.normal(0, 0.3), 0.5)
        lead_time_variance = max(base * 0.2 + np.random.normal(0, 0.1), 0.1)
        rows.append({
            "store_id": r["store_id"],
            "sku_id": r["sku_id"],
            "supplier_id": f"SUP-{r['category'].upper()}",
            "lead_time_days": round(lead_time, 2),
            "lead_time_variance": round(lead_time_variance, 2),
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False)
    print(f"Generated {len(df)} supplier lead time rows")
    print(df.head())


if __name__ == "__main__":
    main()
