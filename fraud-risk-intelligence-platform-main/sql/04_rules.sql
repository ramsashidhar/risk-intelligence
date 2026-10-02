-- 04_rules.sql – interpretable rule-based risk score (the ML baseline)
DROP VIEW IF EXISTS txn_risk_rules;

CREATE VIEW txn_risk_rules AS
WITH scored AS (
    SELECT
        trans_num, cc_num, trans_time, amt, category, is_fraud,
        amt_zscore, txn_count_24h, home_merchant_km, is_night,

        -- transparent rule flags: the "why" behind each alert
        (amt_zscore >= 3)     AS rule_amount_anomaly,
        (txn_count_24h >= 10) AS rule_velocity_spike,
        (amt >= 500)          AS rule_large_amount,
        is_night              AS rule_night_txn,

        -- weighted score; weights reflect Phase 2 signal strength
        (CASE WHEN amt_zscore >= 3 THEN 50
              WHEN amt_zscore >= 2 THEN 25 ELSE 0 END)
      + (CASE WHEN txn_count_24h >= 10 THEN 20
              WHEN txn_count_24h >= 5  THEN 10 ELSE 0 END)
      + (CASE WHEN amt >= 500 THEN 20 ELSE 0 END)
      + (CASE WHEN is_night THEN 10 ELSE 0 END) AS risk_score
    FROM txn_features
)
SELECT *,
    CASE WHEN risk_score >= 60 THEN 'HIGH'
         WHEN risk_score >= 30 THEN 'MEDIUM'
         ELSE 'LOW' END AS risk_band
FROM scored;