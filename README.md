# Accesco Living Inventory Management System (IMS) — Demand Forecasting & Replenishment Pipeline

An end-to-end machine learning and operational pipeline for quantity-level demand forecasting, inventory replenishment recommendations, and multi-check anomaly detection across multi-store dark store networks (e.g., Bangalore scope: `DS-BLR-01`, `DS-BLR-02`, `DS-BLR-03`).

## Project Structure
├── schema/
│   └── demand_forecast_schema.sql         -- Database table definitions (Store, SKU, Sales, Snapshots, Lead Times)
├── generate_synthetic_data.py             -- Generates synthetic sales transactions
├── generate_synthetic_lead_times.py       -- Generates synthetic supplier lead times & variance
├── generate_inventory_snapshots.py        -- Generates synthetic inventory on-hand & in-transit snapshots
├── feature_engineering.py                 -- Transforms raw sales into a dense daily feature panel
├── train_demand_model.py                  -- Trains an XGBoost regressor using time-based splitting
├── generate_forecasts.py                  -- Runs inference to output next-day quantity forecasts
├── replenishment_engine.py                -- Calculates safety stock, reorder points (ROP), and order quantities
├── inject_synthetic_anomalies.py          -- Utility to plant known anomalies for testing detector accuracy
├── anomaly_detection.py                   -- Performs Z-score checks, inventory discrepancy checks, and Isolation Forest
└── README.md                              -- Project documentation