-- 01_schema.sql – raw landing table + curated transactions table

-- Re-runnable: clear old versions first
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS staging_transactions;

-- 1. Staging: matches the Sparkov CSV 1:1, no constraints (fast COPY)
CREATE TABLE staging_transactions (
    row_id                INTEGER,
    trans_date_trans_time TIMESTAMP,
    cc_num                BIGINT,
    merchant              TEXT,
    category              TEXT,
    amt                   NUMERIC(12,2),
    first_name            TEXT,
    last_name             TEXT,
    gender                CHAR(1),
    street                TEXT,
    city                  TEXT,
    state                 CHAR(2),
    zip                   TEXT,
    lat                   DOUBLE PRECISION,
    long                  DOUBLE PRECISION,
    city_pop              INTEGER,
    job                   TEXT,
    dob                   DATE,
    trans_num             TEXT,
    unix_time             BIGINT,
    merch_lat             DOUBLE PRECISION,
    merch_long            DOUBLE PRECISION,
    is_fraud              SMALLINT
);

-- 2. Curated: cleaned + constrained. PII columns (name, street) dropped on purpose
CREATE TABLE transactions (
    trans_num   TEXT          PRIMARY KEY,
    trans_time  TIMESTAMP     NOT NULL,
    cc_num      BIGINT        NOT NULL,
    merchant    TEXT,
    category    TEXT,
    amt         NUMERIC(12,2) NOT NULL CHECK (amt >= 0),
    gender      CHAR(1),
    city        TEXT,
    state       CHAR(2),
    zip         TEXT,
    lat         DOUBLE PRECISION,
    long        DOUBLE PRECISION,
    city_pop    INTEGER,
    job         TEXT,
    dob         DATE,
    merch_lat   DOUBLE PRECISION,
    merch_long  DOUBLE PRECISION,
    is_fraud    SMALLINT      NOT NULL CHECK (is_fraud IN (0,1))
);

-- 3. Indexes tuned for the feature queries
CREATE INDEX idx_txn_card_time ON transactions (cc_num, trans_time);

-- Category fraud-rate aggregations
CREATE INDEX idx_txn_category ON transactions (category);

-- Time-range scans for the dashboard
CREATE INDEX idx_txn_time ON transactions (trans_time);

-- Fraud is ~0.5% of rows – a partial index keeps fraud-only lookups tiny
CREATE INDEX idx_txn_fraud ON transactions (trans_time) WHERE is_fraud = 1;