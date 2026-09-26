import sys; sys.path.insert(0,"src")
import pandas as pd, numpy as np, features as F
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
D="data/"; tr=F.clean_orders(pd.read_csv(D+"train.csv")); cu=pd.read_csv(D+"customers.csv"); pr=pd.read_csv(D+"products.csv")
F.CAT0,F.NUM0=F.CAT,F.NUM; F.CAT=F.CAT+["tier","state","note_cat"]; F.NUM=F.NUM+[c for c in F.EXTRA if c not in ["tier","state","note_cat"]]; X,d=F.build(tr,cu,pr); y=tr.returned.values; t=d.order_placed_at
folds=[("2025-11-01","2026-01-01"),("2026-01-01","2026-03-01"),("2026-03-01","2026-05-01"),("2026-05-01","2026-07-01")]
def score(cat,num,C=0.5,raw=False):
    out=[]
    for a,b in folds:
        tri=(t<a).values; tei=((t>=a)&(t<b)).values
        pre=ColumnTransformer([("c",OneHotEncoder(handle_unknown="ignore"),cat),("n",StandardScaler(),num)])
        m=make_pipeline(pre,LogisticRegression(C=C,max_iter=3000)).fit(X[tri],y[tri])
        out.append(roc_auc_score(y[tei],m.predict_proba(X[tei])[:,1]))
    return round(np.mean(out),4)
C0,N0=F.CAT+[c for c in F.EXTRA if c in ["tier","state","note_cat"]],F.NUM+[c for c in F.EXTRA if c not in ["tier","state","note_cat"]]
print("all",score(C0,N0))
for c in C0: print("-",c,score([x for x in C0 if x!=c],N0))
for n in N0: print("-",n,score(C0,[x for x in N0 if x!=n]))
for C in [0.05,0.2,1,5]: print("C",C,score(C0,N0,C))
# paise fix off
X2=X.copy(); 
LC=["sales_channel","payment_mode","family"]
LN=["discount_pct","promised_delivery_days","is_gift","customer_prior_returns","prior_return_rate","shield","customer_prior_orders"]
for C in [0.1,0.5]: print("lean",C,score(LC,LN,C))
print("lean+state",score(LC+["state"],LN,0.1))
print("lean+value",score(LC,LN+["value_to_list","list_price_inr"],0.1))
