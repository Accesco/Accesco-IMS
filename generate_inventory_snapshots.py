# Let's create the inventory_snapshots_synthetic.csv file programmatically right now so the user has it ready.
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)
STORES = ["DS-BLR-01", "DS-BLR-02", "DS-BLR-03"]
SKUS = [
    {"sku_id": "SKU-MILK-500", "base_stock": 100},
    {"sku_id": "SKU-BREAD-400", "base_stock": 80},
    {"sku_id": "SKU-EGG-6PK", "base_stock": 90},
    {"sku_id": "SKU-RICE-1KG", "base_stock": 200},
    {"sku_id": "SKU-CHIPS-100", "base_stock": 150},
    {"sku_id": "SKU-COLA-750", "base_stock": 120},
    {"sku_id": "SKU-DETERGENT-1L", "base_stock": 60},
    {"sku_id": "SKU-BANANA-1KG", "base_stock": 70},
]
N_DAYS = 180
START_DATE = datetime(2026, 1, 1)

inv_rows = []
for store_id in STORES:
    for sku in SKUS:
        stock = sku["base_stock"]
        for day_idx in range(N_DAYS):
            date = START_DATE + timedelta(days=day_idx)
            stock = max(10, stock + np.random.randint(-5, 6))
            inv_rows.append({
                "store_id": store_id,
                "sku_id": sku["sku_id"],
                "snapshot_date": date.date().isoformat(),
                "stock_on_hand": stock,
                "stock_in_transit": np.random.randint(0, 20)
            })

inv_df = pd.DataFrame(inv_rows)
inv_df.to_csv("inventory_snapshots_synthetic.csv", index=False)
print("Successfully created inventory_snapshots_synthetic.csv with", len(inv_df), "rows.")