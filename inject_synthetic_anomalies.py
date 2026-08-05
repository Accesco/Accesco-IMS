"""
Injects a small number of known anomalies into copies of the synthetic
sales/inventory data, with a ground-truth label file, so
anomaly_detection.py can be checked against known answers instead of
just "did it flag *something*."

This step exists only for dev/validation — real anomaly detection runs
directly against sales_transactions / inventory_snapshots, no injection.
"""
import numpy as np
import pandas as pd

np.random.seed(23)

SALES_PATH = "sales_transactions_synthetic.csv"
INVENTORY_PATH = "inventory_snapshots_synthetic.csv"

SALES_OUT = "sales_transactions_with_anomalies.csv"
INVENTORY_OUT = "inventory_snapshots_with_anomalies.csv"
GROUND_TRUTH_OUT = "anomaly_ground_truth.csv"

def main():
    sales = pd.read_csv(SALES_PATH)
    inventory = pd.read_csv(INVENTORY_PATH)
    ground_truth = []

    pairs = sales[["store_id", "sku_id"]].drop_duplicates().reset_index(drop=True)

    # 1. Sales spike: one store-sku, one day, 6x normal volume (e.g. bulk
    #    order or data entry error)
    r = pairs.sample(1, random_state=1).iloc[0]
    mask = (sales.store_id == r.store_id) & (sales.sku_id == r.sku_id)
    idx = sales[mask].sort_values("txn_date").index[90]
    sales.loc[idx, "qty_sold"] = int(sales.loc[idx, "qty_sold"] * 6)
    ground_truth.append({"store_id": r.store_id, "sku_id": r.sku_id,
                          "date": sales.loc[idx, "txn_date"], "type": "sales_spike"})

    # 2. Sales drop: another store-sku, sudden near-zero for a day
    #    (e.g. stockout not reflected in inventory, or a system outage)
    r2 = pairs.sample(1, random_state=2).iloc[0]
    mask2 = (sales.store_id == r2.store_id) & (sales.sku_id == r2.sku_id)
    idx2 = sales[mask2].sort_values("txn_date").index[100]
    sales.loc[idx2, "qty_sold"] = 1
    ground_truth.append({"store_id": r2.store_id, "sku_id": r2.sku_id,
                          "date": sales.loc[idx2, "txn_date"], "type": "sales_drop"})

    # 3. Inventory shrinkage: unexplained stock drop not matched by sales
    #    or a recorded restock (e.g. theft or miscounted stock)
    r3 = pairs.sample(1, random_state=3).iloc[0]
    inv_mask = (inventory.store_id == r3.store_id) & (inventory.sku_id == r3.sku_id)
    inv_rows = inventory[inv_mask].sort_values("snapshot_date")
    shrink_idx = inv_rows.index[70]
    inventory.loc[shrink_idx, "stock_on_hand"] = max(
        int(inventory.loc[shrink_idx, "stock_on_hand"]) - 50, 0
    )
    ground_truth.append({"store_id": r3.store_id, "sku_id": r3.sku_id,
                          "date": inventory.loc[shrink_idx, "snapshot_date"], "type": "inventory_shrinkage"})

    sales.to_csv(SALES_OUT, index=False)
    inventory.to_csv(INVENTORY_OUT, index=False)
    pd.DataFrame(ground_truth).to_csv(GROUND_TRUTH_OUT, index=False)

    print("Injected anomalies:")
    for g in ground_truth:
        print(f"  {g}")


if __name__ == "__main__":
    main()
