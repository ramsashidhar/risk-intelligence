import pandas as pd
from db import get_engine

FEATURES = [
    "amt", "amt_zscore", "txn_count_24h", "txn_count_7d", "amt_sum_24h",
    "cardholder_age", "txn_hour", "is_weekend", "is_night", "home_merchant_km",
]

def load_feature_matrix():
    df = pd.read_sql("SELECT * FROM feature_matrix", get_engine())
    # single-transaction cards have no amount deviation -> neutral 0
    df["amt_zscore"] = df["amt_zscore"].fillna(0)
    return df

def time_split(df, cutoff="2020-04-01"):
    """Train on earlier transactions, test on later ones — no lookahead."""
    train = df[df["trans_time"] <  cutoff].copy()
    test  = df[df["trans_time"] >= cutoff].copy()
    return train, test

if __name__ == "__main__":
    df = load_feature_matrix()
    train, test = time_split(df)
    for name, part in [("train", train), ("test", test)]:
        n, fraud = len(part), int(part["is_fraud"].sum())
        print(f"{name}: {n:,} rows | {fraud:,} fraud ({100*fraud/n:.3f}%)")