import os
import numpy as np
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.metrics import average_precision_score, roc_auc_score, precision_recall_curve
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from features import load_feature_matrix, time_split, FEATURES

RULE_RECALL = 0.439

def prec_at_recall(y, scores, target=RULE_RECALL):
    prec, rec, _ = precision_recall_curve(y, scores)
    return prec[np.argmin(np.abs(rec - target))]

def evaluate(name, y, scores):
    ap, roc = average_precision_score(y, scores), roc_auc_score(y, scores)
    p = prec_at_recall(y, scores)
    print(f"{name:24s} PR-AUC={ap:.3f}  ROC-AUC={roc:.3f}  precision@44%recall={p*100:.1f}%")
    return ap

def main():
    train, test = time_split(load_feature_matrix())
    Xtr, ytr = train[FEATURES], train["is_fraud"]
    Xte, yte = test[FEATURES], test["is_fraud"]
    spw = (ytr == 0).sum() / (ytr == 1).sum()
    print(f"Model bake-off  (train {len(Xtr):,} / test {len(Xte):,})\n")

    # 1. Logistic Regression – linear baseline
    lr = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000))
    lr.fit(Xtr, ytr)
    evaluate("Logistic Regression", yte, lr.predict_proba(Xte)[:, 1])

    # 2. Random Forest – bagging ensemble
    rf = RandomForestClassifier(n_estimators=200, max_depth=12, class_weight="balanced",
                                n_jobs=-1, random_state=42)
    rf.fit(Xtr, ytr)
    evaluate("Random Forest", yte, rf.predict_proba(Xte)[:, 1])

    # 3. XGBoost – gradient boosting
    xgb = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1, scale_pos_weight=spw,
                        eval_metric="aucpr", tree_method="hist", n_jobs=-1)
    xgb.fit(Xtr, ytr)
    evaluate("XGBoost", yte, xgb.predict_proba(Xte)[:, 1])

    # 4. LightGBM – gradient boosting
    lgb = LGBMClassifier(n_estimators=400, learning_rate=0.05, scale_pos_weight=spw,
                         n_jobs=-1, verbose=-1)
    lgb.fit(Xtr, ytr)
    evaluate("LightGBM", yte, lgb.predict_proba(Xte)[:, 1])

    # 5. Isolation Forest – UNSUPERVISED anomaly baseline (never sees the labels)
    iso = IsolationForest(n_estimators=200, contamination=float(ytr.mean()),
                          random_state=42, n_jobs=-1)
    iso.fit(Xtr)
    evaluate("Isolation Forest (unsup.)", yte, -iso.score_samples(Xte))

    print(f"\nRule baseline:           precision=17.0%  recall=43.9%")

    # keep XGBoost as the production model
    os.makedirs("models", exist_ok=True)
    joblib.dump({"model": xgb, "features": FEATURES, "name": "XGBoost"}, "models/xgb_fraud.pkl")
    print("\nSaved models/xgb_fraud.pkl (XGBoost)")

if __name__ == "__main__":
    main()