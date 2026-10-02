"""
Prep scored fraud data for Tableau dashboard.
Input:  data/processed/scored.parquet (risk.py), models/xgb_fraud.pkl (train.py)
Output: tableau_data/*.csv
"""
import os
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import (confusion_matrix, roc_auc_score, average_precision_score,
                             precision_score, recall_score, f1_score)

SCORED_FILE = "data/processed/scored.parquet"
MODEL_FILE  = "models/xgb_fraud.pkl"
OUTPUT_DIR  = "tableau_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

scored = pd.read_parquet(SCORED_FILE)
bundle = joblib.load(MODEL_FILE)
model  = bundle["model"]
print(f"Scored: {len(scored):,} rows | Model: {bundle['name']}")

#  01 metrics (fraud-class, not weighted) 
y_true = scored["is_fraud"]
proba  = scored["p_fraud"]
y_pred = (proba >= 0.5).astype(int)
tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

metrics = pd.DataFrame({
    "Metric": ["Total transactions", "Fraud cases", "Fraud rate (%)",
               "True positives", "False positives", "True negatives", "False negatives",
               "Fraud precision @0.5", "Fraud recall @0.5", "Fraud F1 @0.5",
               "PR-AUC", "ROC-AUC"],
    "Value": [len(scored), int(y_true.sum()), round(100 * y_true.mean(), 3),
              int(tp), int(fp), int(tn), int(fn),
              round(precision_score(y_true, y_pred, zero_division=0), 3),  # tp/(tp+fp)
              round(recall_score(y_true, y_pred), 3),                      # tp/(tp+fn)
              round(f1_score(y_true, y_pred), 3),
              round(average_precision_score(y_true, proba), 3),            # PR-AUC = honest headline
              round(roc_auc_score(y_true, proba), 3)],
})
metrics.to_csv(f"{OUTPUT_DIR}/01_metrics.csv", index=False)

# 02 risk tiers
scored["risk_level"] = pd.cut(scored["p_fraud"], bins=[0, 0.2, 0.5, 0.8, 1.0],
                              labels=["Low", "Medium", "High", "Critical"], include_lowest=True)
risk = scored["risk_level"].value_counts().reindex(["Critical", "High", "Medium", "Low"]).reset_index()
risk.columns = ["Risk_Level", "Count"]
risk["Percentage"] = round(100 * risk["Count"] / len(scored), 3)
risk.to_csv(f"{OUTPUT_DIR}/02_risk_distribution.csv", index=False)

# temporal
t = pd.to_datetime(scored["trans_time"])
scored["date"], scored["hour"], scored["dow"] = t.dt.date, t.dt.hour, t.dt.day_name()

# 03 daily
daily = scored.groupby("date").agg(
    Avg_Fraud_Prob=("p_fraud", "mean"), Transactions=("p_fraud", "count"),
    Actual_Frauds=("is_fraud", "sum"), Total_Amount=("amt", "sum")).reset_index()
daily.rename(columns={"date": "Date"}).to_csv(f"{OUTPUT_DIR}/03_daily_trends.csv", index=False)

# 04 hourly
hourly = scored.groupby("hour").agg(
    Avg_Fraud_Prob=("p_fraud", "mean"), Count=("is_fraud", "count"),
    Fraud_Rate_Pct=("is_fraud", lambda s: round(100 * s.mean(), 3))).reset_index()
hourly.rename(columns={"hour": "Hour"}).to_csv(f"{OUTPUT_DIR}/04_hourly_pattern.csv", index=False)

# 05 patterns
dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
dow = scored.groupby("dow").agg(
    Avg_Fraud_Prob=("p_fraud", "mean"), Count=("is_fraud", "count"),
    Fraud_Rate_Pct=("is_fraud", lambda s: round(100 * s.mean(), 3))).reset_index()
dow["dow"] = pd.Categorical(dow["dow"], categories=dow_order, ordered=True)
dow = dow.sort_values("dow").rename(columns={"dow": "Day"})
dow.to_csv(f"{OUTPUT_DIR}/05_dow_pattern.csv", index=False)

# 06 amount buckets (meaningful $ bins, with fraud rate)
edges  = [0, 50, 100, 250, 500, 1000, np.inf]
labels = ["$0-50", "$50-100", "$100-250", "$250-500", "$500-1k", "$1k+"]
scored["amt_bucket"] = pd.cut(scored["amt"], bins=edges, labels=labels, right=False)
amt = scored.groupby("amt_bucket", observed=False).agg(
    Transactions=("is_fraud", "size"), Frauds=("is_fraud", "sum"),
    Avg_Fraud_Prob=("p_fraud", "mean")).reset_index()
amt["Fraud_Rate_Pct"] = round(100 * amt["Frauds"] / amt["Transactions"], 3)
amt["Sort"] = range(len(amt))   # gives Tableau a clean bin order
amt.rename(columns={"amt_bucket": "Amount_Bucket"}).to_csv(f"{OUTPUT_DIR}/06_amount_bins.csv", index=False)

# 07 confusion matrix
pd.DataFrame({
    "Actual":    ["Fraud", "Fraud", "Legitimate", "Legitimate"],
    "Predicted": ["Fraud", "Legitimate", "Fraud", "Legitimate"],
    "Count":     [tp, fn, fp, tn],
}).to_csv(f"{OUTPUT_DIR}/07_confusion_matrix.csv", index=False)

# 08 feature importance
pd.DataFrame({"Feature": bundle["features"], "Importance": model.feature_importances_}) \
    .sort_values("Importance", ascending=False) \
    .to_csv(f"{OUTPUT_DIR}/08_feature_importance.csv", index=False)

# 09 probability distribution
edges = [i / 10 for i in range(11)]
plabels = [f"{i/10:.1f}-{(i+1)/10:.1f}" for i in range(10)]
scored["prob_bin"] = pd.cut(scored["p_fraud"], bins=edges, labels=plabels, include_lowest=True)
prob = scored["prob_bin"].value_counts().reindex(plabels).reset_index()
prob.columns = ["Probability_Bin", "Count"]
prob.to_csv(f"{OUTPUT_DIR}/09_prob_distribution.csv", index=False)

# 10 category fraud rate 
cat = scored.groupby("category").agg(
    Transactions=("is_fraud", "size"), Frauds=("is_fraud", "sum")).reset_index()
cat["Fraud_Rate_Pct"] = round(100 * cat["Frauds"] / cat["Transactions"], 3)
cat = cat.sort_values("Fraud_Rate_Pct", ascending=False).rename(columns={"category": "Category"})
cat.to_csv(f"{OUTPUT_DIR}/10_category_fraud.csv", index=False)

files = sorted(os.listdir(OUTPUT_DIR))
print(f"\nExported {len(files)} CSVs to {os.path.abspath(OUTPUT_DIR)}/")
for f in files:
    print("  -", f)