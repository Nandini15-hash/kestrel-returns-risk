"""Train the final model on all labelled orders and write predictions.csv.
Usage:  python src/train.py            (expects the pack's CSVs in ./data)"""
import sys, json, os; sys.path.insert(0, os.path.dirname(__file__))
import joblib, numpy as np, pandas as pd
from features import clean_orders, build, CAT, NUM
from model import make_logreg
D = os.path.join(os.path.dirname(__file__), "..", "data") + "/"
tr = clean_orders(pd.read_csv(D + "train.csv"))
te = pd.read_csv(D + "test_unlabelled.csv")
cu = pd.read_csv(D + "customers.csv"); pr = pd.read_csv(D + "products.csv")
X, d = build(tr, cu, pr); y = tr["returned"].values
m = make_logreg().fit(X, y)
Xt, dt = build(te, cu, pr)
p = m.predict_proba(Xt)[:, 1]
sub = pd.DataFrame({"order_id": te["order_id"].values, "score": np.round(p, 5)})
sample = pd.read_csv(D + "sample_submission.csv")
assert set(sub.order_id) == set(sample.order_id) and len(sub) == len(sample), "id mismatch vs sample"
sub = sample[["order_id"]].merge(sub, on="order_id")
sub.to_csv(os.path.join(D, "..", "predictions.csv"), index=False)
# Save model + reference values the API needs for explanations
ref = {"means": {c: float(X[c].mean()) for c in NUM},
       "cats": {c: sorted(map(str, X[c].cat.categories)) for c in CAT},
       "base_rate": float(y.mean()), "modes": {c: str(X[c].mode()[0]) for c in CAT},
       "call_cut": float(np.quantile(p, 0.80)),   # top-20% of recent orders → call
       "families": dict(zip(pr.sku, pr.family)), "skus": sorted(pr.sku)}
joblib.dump({"model": m, "ref": ref}, os.path.join(D, "..", "service", "model.joblib"))
print("train rows", len(tr), "test rows", len(sub), "mean score", p.mean().round(4), "call cut", round(ref["call_cut"], 3))
print(sub.score.describe().round(3))
