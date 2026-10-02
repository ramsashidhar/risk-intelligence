"""
export_web.py - reads the scored test set and writes data.js for the dashboard.
Run from the project root:  python export_web.py
"""
import json, os
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, average_precision_score

FLOOR = 0.5
SCORED = "data/processed/scored.parquet"
MODEL = "models/xgb_fraud.pkl"
OUT_DIR = "dashboard"
OUT = os.path.join(OUT_DIR, "data.js")

df = pd.read_parquet(SCORED)
df["trans_time"] = pd.to_datetime(df["trans_time"])

total_fraud = int(df["is_fraud"].sum())
total_fraud_loss = float(df.loc[df.is_fraud == 1, "amt"].sum())

gated = df[df["p_fraud"] >= FLOOR].copy()
alerts = [{
    "t": r.trans_time.strftime("%Y-%m-%d %H:%M"),
    "card": str(int(r.cc_num))[-4:],
    "cat": r.category,
    "amt": round(float(r.amt), 2),
    "p": round(float(r.p_fraud), 4),
    "el": round(float(r.expected_loss)),
    "f": int(r.is_fraud),
} for r in gated.itertuples()]

cat = (df.groupby("category")["is_fraud"].mean() * 100).sort_values(ascending=False).head(10)
catRates = [{"cat": k, "rate": round(float(v), 3)} for k, v in cat.items()]

wk = df[df.is_fraud == 1].set_index("trans_time").resample("W").size()
weekly = [{"w": idx.strftime("%Y-%m-%d"), "n": int(v)} for idx, v in wk.items()]

def box_stats(s):
    q1, med, q3 = s.quantile(.25), s.quantile(.5), s.quantile(.75)
    iqr = q3 - q1
    return {"q1": float(q1), "med": float(med), "q3": float(q3),
            "lf": float(max(s.min(), q1 - 1.5 * iqr)),
            "uf": float(min(s.max(), q3 + 1.5 * iqr))}

amountBox = {"legit": box_stats(df.loc[df.is_fraud == 0, "amt"]),
             "fraud": box_stats(df.loc[df.is_fraud == 1, "amt"])}

prec, rec, _ = precision_recall_curve(df["is_fraud"], df["p_fraud"])
ap = float(average_precision_score(df["is_fraud"], df["p_fraud"]))
sel = np.linspace(0, len(prec) - 1, 200).astype(int)
pr = {"recall": [round(float(rec[i]), 4) for i in sel],
      "precision": [round(float(prec[i]), 4) for i in sel], "ap": round(ap, 3)}

featImp = []
if os.path.exists(MODEL):
    import joblib
    b = joblib.load(MODEL)
    fi = pd.Series(b["model"].feature_importances_, index=b["features"]).sort_values(ascending=False).head(8)
    featImp = [{"f": k, "v": round(float(v), 3)} for k, v in fi.items()]

pred = (df["p_fraud"] >= 0.5).astype(int)
cm = {"tn": int(((pred == 0) & (df.is_fraud == 0)).sum()),
      "fp": int(((pred == 1) & (df.is_fraud == 0)).sum()),
      "fn": int(((pred == 0) & (df.is_fraud == 1)).sum()),
      "tp": int(((pred == 1) & (df.is_fraud == 1)).sum())}

DASH = {"totalFraud": total_fraud, "totalFraudLoss": round(total_fraud_loss),
        "rulePrecision": 17.0, "ruleRecall": 0.439,
        "alerts": alerts, "catRates": catRates, "weekly": weekly,
        "amountBox": amountBox, "pr": pr, "featImp": featImp, "cm": cm}

os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT, "w") as f:
    f.write("window.DASH = " + json.dumps(DASH) + ";\n")

print(f"Wrote {OUT}  ({len(alerts):,} alerts, {total_fraud:,} fraud in test set)")