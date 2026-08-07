-- =====================================================================
-- Demand Forecasting Schema — Accesco Living IMS
-- Extends the existing predictive-replenishment schema (urgent-reorder
-- classifier) with tables needed for quantity-level demand forecasting.
-- Store scope: DS-BLR-01, DS-BLR-02, DS-BLR-03 (Bangalore dark stores)
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Master data (dimensions)
-- ---------------------------------------------------------------------

CREATE TABLE store_master (
    store_id            VARCHAR(16) PRIMARY KEY,      -- e.g. 'DS-BLR-01'
    store_name          VARCHAR(100) NOT NULL,
    city                VARCHAR(50)  NOT NULL,
    pincode             VARCHAR(10),
    latitude            DECIMAL(9,6),
    longitude           DECIMAL(9,6),
    is_active           BOOLEAN DEFAULT TRUE,
    opened_at           DATE
);

CREATE TABLE sku_master (
    sku_id              VARCHAR(24) PRIMARY KEY,
    sku_name            VARCHAR(200) NOT NULL,
    category            VARCHAR(50),
    sub_category        VARCHAR(50),
    unit_of_measure     VARCHAR(16),                   -- 'pc', 'kg', 'ltr'
    unit_cost           DECIMAL(10,2),
    shelf_life_days     INT,                           -- NULL if non-perishable
    is_active           BOOLEAN DEFAULT TRUE
);

-- ---------------------------------------------------------------------
-- 2. Fact tables (raw activity, append-only)
-- ---------------------------------------------------------------------

CREATE TABLE sales_transactions (
    txn_id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    store_id            VARCHAR(16) NOT NULL REFERENCES store_master(store_id),
    sku_id              VARCHAR(24) NOT NULL REFERENCES sku_master(sku_id),
    txn_ts              TIMESTAMP NOT NULL,
    qty_sold            INT NOT NULL,
    unit_price          DECIMAL(10,2),
    promo_flag          BOOLEAN DEFAULT FALSE,
    channel             VARCHAR(16) DEFAULT 'app'      -- 'app', 'web', 'walk-in'
);

CREATE TABLE inventory_snapshots (
    snapshot_id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    store_id            VARCHAR(16) NOT NULL REFERENCES store_master(store_id),
    sku_id              VARCHAR(24) NOT NULL REFERENCES sku_master(sku_id),
    snapshot_ts         TIMESTAMP NOT NULL,
    stock_on_hand       INT NOT NULL,
    stock_in_transit    INT DEFAULT 0,
    reorder_point       INT,
    last_restock_ts     TIMESTAMP
);

CREATE TABLE supplier_lead_times (
    store_id            VARCHAR(16) NOT NULL REFERENCES store_master(store_id),
    sku_id              VARCHAR(24) NOT NULL REFERENCES sku_master(sku_id),
    supplier_id         VARCHAR(24),
    lead_time_days      DECIMAL(5,2) NOT NULL,
    lead_time_variance  DECIMAL(5,2),
    PRIMARY KEY (store_id, sku_id, supplier_id)
);

-- ---------------------------------------------------------------------
-- 3. Feature table (materialized daily, one row per store-sku-date)
--    This is what feature_engineering.py builds and what the model reads.
-- ---------------------------------------------------------------------

CREATE TABLE demand_features_daily (
    store_id            VARCHAR(16) NOT NULL,
    sku_id              VARCHAR(24) NOT NULL,
    feature_date        DATE NOT NULL,

    -- target (only populated for historical/training rows)
    qty_sold_next_day   INT,

    -- recent sales behaviour
    qty_sold_lag_1      INT,
    qty_sold_lag_7      INT,
    qty_sold_lag_14     INT,
    rolling_mean_7d     DECIMAL(10,2),
    rolling_mean_14d    DECIMAL(10,2),
    rolling_mean_30d    DECIMAL(10,2),
    rolling_std_7d      DECIMAL(10,2),
    days_since_last_sale INT,

    -- calendar
    day_of_week         SMALLINT,
    is_weekend          BOOLEAN,
    day_of_month        SMALLINT,
    month               SMALLINT,
    is_month_start      BOOLEAN,
    is_holiday          BOOLEAN,

    -- context
    promo_active        BOOLEAN,
    current_stock_on_hand INT,
    days_since_restock  INT,
    price               DECIMAL(10,2),

    -- sku static features (denormalized for model convenience)
    category            VARCHAR(50),
    shelf_life_days     INT,

    PRIMARY KEY (store_id, sku_id, feature_date)
);

-- ---------------------------------------------------------------------
-- 4. Model output table
-- ---------------------------------------------------------------------

CREATE TABLE demand_forecast_output (
    store_id            VARCHAR(16) NOT NULL,
    sku_id              VARCHAR(24) NOT NULL,
    forecast_date       DATE NOT NULL,          -- date being predicted
    forecast_generated_at TIMESTAMP NOT NULL,
    predicted_qty       DECIMAL(10,2) NOT NULL,
    model_version       VARCHAR(32) NOT NULL,   -- e.g. 'xgb-demand-v1'
    PRIMARY KEY (store_id, sku_id, forecast_date, model_version)
);
