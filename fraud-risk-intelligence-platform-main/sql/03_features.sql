-- 03_features.sql – engineered fraud features (materialized view)

DROP MATERIALIZED VIEW IF EXISTS txn_features;

CREATE MATERIALIZED VIEW txn_features AS
WITH base AS (
    SELECT
        trans_num, cc_num, trans_time, amt, category, is_fraud,
        lat, long, merch_lat, merch_long, dob,
        -- previous txn on the same card, for impossible-travel
        LAG(trans_time) OVER w AS prev_time,
        LAG(merch_lat)  OVER w AS prev_merch_lat,
        LAG(merch_long) OVER w AS prev_merch_long
    FROM transactions
    WINDOW w AS (PARTITION BY cc_num ORDER BY trans_time)
)
SELECT
    trans_num, cc_num, trans_time, amt, category, is_fraud,

    -- time-of-day
    EXTRACT(HOUR FROM trans_time)::int             AS txn_hour,
    EXTRACT(DOW  FROM trans_time)::int             AS txn_dow,
    (EXTRACT(DOW  FROM trans_time) IN (0,6))        AS is_weekend,
    (EXTRACT(HOUR FROM trans_time) BETWEEN 0 AND 5) AS is_night,

    -- cardholder age at time of txn
    EXTRACT(YEAR FROM AGE(trans_time, dob))::int   AS cardholder_age,

    -- velocity: card activity in the trailing window (incl. this txn)
    COUNT(*) OVER win_24h                           AS txn_count_24h,
    COUNT(*) OVER win_7d                            AS txn_count_7d,
    SUM(amt) OVER win_24h                           AS amt_sum_24h,

    -- amount deviation: how unusual is this amount for this card
    ROUND(
        (amt - AVG(amt) OVER card)
        / NULLIF(STDDEV_SAMP(amt) OVER card, 0)
    , 3)                                            AS amt_zscore,

    -- geo: cardholder home -> merchant distance, km (haversine)
    ROUND((2 * 6371 * ASIN(SQRT(
        POWER(SIN(RADIANS(merch_lat - lat) / 2), 2) +
        COS(RADIANS(lat)) * COS(RADIANS(merch_lat)) *
        POWER(SIN(RADIANS(merch_long - long) / 2), 2)
    )))::numeric, 2)                                AS home_merchant_km,

    -- geo: implied speed since previous txn (impossible travel)
    CASE
      WHEN prev_time IS NULL OR trans_time = prev_time THEN NULL
      ELSE ROUND((
        (2 * 6371 * ASIN(SQRT(
            POWER(SIN(RADIANS(merch_lat - prev_merch_lat) / 2), 2) +
            COS(RADIANS(prev_merch_lat)) * COS(RADIANS(merch_lat)) *
            POWER(SIN(RADIANS(merch_long - prev_merch_long) / 2), 2)
        )))
        / (EXTRACT(EPOCH FROM (trans_time - prev_time)) / 3600.0)
      )::numeric, 1)
    END                                             AS implied_kmh

FROM base
WINDOW
    card    AS (PARTITION BY cc_num),
    win_24h AS (PARTITION BY cc_num ORDER BY trans_time
                RANGE BETWEEN INTERVAL '24 hours' PRECEDING AND CURRENT ROW),
    win_7d  AS (PARTITION BY cc_num ORDER BY trans_time
                RANGE BETWEEN INTERVAL '7 days'  PRECEDING AND CURRENT ROW);

-- indexes on the view (unique one also enables CONCURRENT refresh later)
CREATE UNIQUE INDEX idx_feat_trans ON txn_features (trans_num);
CREATE INDEX        idx_feat_fraud ON txn_features (is_fraud);