-- 02_load.sql – load Sparkov CSV into staging, then curate into transactions

-- Re-runnable: clear staging first so re-runs don't append duplicates
TRUNCATE staging_transactions;

-- Bulk load the raw CSV. \copy is client-side
-- (server-side COPY would need superuser). 
-- Path is relative to where you launch psql
\copy staging_transactions FROM 'data/raw/fraudTrain.csv' WITH (FORMAT csv, HEADER true)

-- Curate into the clean table: drop PII (name, street) and redundant cols
TRUNCATE transactions;
INSERT INTO transactions (
    trans_num, trans_time, cc_num, merchant, category, amt,
    gender, city, state, zip, lat, long, city_pop, job, dob,
    merch_lat, merch_long, is_fraud
)
SELECT
    trans_num, trans_date_trans_time, cc_num, merchant, category, amt,
    gender, city, state, zip, lat, long, city_pop, job, dob,
    merch_lat, merch_long, is_fraud
FROM staging_transactions;