-- 05_feature_matrix.sql — clean modeling view + dashboard metadata
DROP VIEW IF EXISTS feature_matrix;

CREATE VIEW feature_matrix AS
SELECT
    trans_num,
    trans_time,
    cc_num,
    category,
    amt,
    amt_zscore,
    txn_count_24h,
    txn_count_7d,
    amt_sum_24h,
    cardholder_age,
    txn_hour,
    is_weekend::int AS is_weekend,
    is_night::int   AS is_night,
    home_merchant_km,
    is_fraud
FROM txn_features;