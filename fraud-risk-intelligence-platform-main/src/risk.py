import pandas as pd
import joblib
from features import load_feature_matrix, time_split

FLOOR = 0.5

def score(df, bundle):
    df = df.copy()
    df["p_fraud"] = bundle["model"].predict_proba(df[bundle["features"]])[:, 1]
    df["expected_loss"] = df["p_fraud"] * df["amt"]
    return df

def alert_budget(scored, ks=(100, 500, 1000, 5000)):
    queue = (scored[scored["p_fraud"] >= FLOOR]
             .sort_values("expected_loss", ascending=False).reset_index(drop=True))
    total_fraud = int(scored["is_fraud"].sum())
    total_loss  = scored.loc[scored["is_fraud"] == 1, "amt"].sum()
    rows = []
    for k in ks:
        top = queue.head(k)
        caught = int(top["is_fraud"].sum())
        loss_caught = top.loc[top["is_fraud"] == 1, "amt"].sum()
        rows.append({"alerts_reviewed": min(k, len(queue)), "fraud_caught": caught,
                     "precision_pct": round(100*caught/max(len(top),1),1),
                     "fraud_recall_pct": round(100*caught/total_fraud,1),
                     "loss_recovered_pct": round(100*loss_caught/total_loss,1)})
    return pd.DataFrame(rows)

def main():
    bundle = joblib.load("models/xgb_fraud.pkl")
    _, test = time_split(load_feature_matrix())
    scored = score(test, bundle)

    print("Alert-budget analysis (gated queue, ranked by expected loss):\n")
    print(alert_budget(scored).to_string(index=False))

    # full scored test set — powers the alert queue (filtered to p>=FLOOR
    # in the app) AND the new analytical charts
    cols = ["trans_time", "cc_num", "category", "amt",
            "p_fraud", "expected_loss", "is_fraud"]
    scored[cols].to_parquet("data/processed/scored.parquet", index=False)
    print(f"\nSaved data/processed/scored.parquet ({len(scored):,} rows)")

if __name__ == "__main__":
    main()