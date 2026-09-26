"""Rolling-origin validation: train on everything before a cut, test on the next 2 months."""
import sys, json; sys.path.insert(0, "src")
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from features import *
from model import make_logreg, LGB_PARAMS
D="data/"
tr=clean_orders(pd.read_csv(D+"train.csv")); cu=pd.read_csv(D+"customers.csv"); pr=pd.read_csv(D+"products.csv")
X,d=build(tr,cu,pr); y=tr["returned"].values; t=d["order_placed_at"]
folds=[("2025-11-01","2026-01-01"),("2026-01-01","2026-03-01"),("2026-03-01","2026-05-01"),("2026-05-01","2026-07-01")]
rows=[]; oof=[]
for a,b in folds:
    tri=(t<a).values; tei=((t>=a)&(t<b)).values
    lr=make_logreg().fit(X[tri],y[tri]); p_lr=lr.predict_proba(X[tei])[:,1]
    gb=lgb.LGBMClassifier(**LGB_PARAMS).fit(X[tri],y[tri]); p_gb=gb.predict_proba(X[tei])[:,1]
    for name,p in [("logreg",p_lr),("lgbm",p_gb),("blend",0.7*p_lr+0.3*p_gb)]:
        rows.append(dict(fold=f"{a[:7]}..{b[:7]}",model=name,n=int(tei.sum()),base_rate=round(y[tei].mean(),3),
                         auc=roc_auc_score(y[tei],p),pr_auc=average_precision_score(y[tei],p),brier=brier_score_loss(y[tei],p)))
    oof.append(pd.DataFrame(dict(order_id=d.order_id[tei].values,y=y[tei],p=p_lr,shield=d.shield[tei].values,
        family=d.family[tei].values,payment=d.payment_mode[tei].values,prior_returns=d.customer_prior_returns[tei].values,fold=a[:7])))
r=pd.DataFrame(rows); print(r.round(4).to_string())
s=r.groupby("model")[["auc","pr_auc","brier"]].agg(["mean","std"]).round(4); print(s)
r.round(4).to_csv("evidence/rolling_validation.csv",index=False)
pd.concat(oof).to_csv("evidence/oof_predictions.csv",index=False)
