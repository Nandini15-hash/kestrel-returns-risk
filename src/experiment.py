import sys, json; sys.path.insert(0, "src")
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from features import *
D="data/"
tr=pd.read_csv(D+"train.csv"); cu=pd.read_csv(D+"customers.csv"); pr=pd.read_csv(D+"products.csv")
res={}
raw=tr.copy()
tr=clean_orders(tr)
X,d=build(tr,cu,pr); y=tr["returned"].values
cut=d["order_placed_at"]>="2026-03-01"
Xa,Xb,ya,yb=X[~cut],X[cut],y[~cut],y[cut]
P=dict(n_estimators=300,learning_rate=0.03,num_leaves=15,min_child_samples=40,subsample=0.8,subsample_freq=1,colsample_bytree=0.8,reg_lambda=5,verbose=-1)
def ev(name,p): res[name]=dict(auc=round(roc_auc_score(yb,p),4),pr_auc=round(average_precision_score(yb,p),4)); print(name,res[name])
ev("baseline_prior_returns", Xb.customer_prior_returns+Xb.discount_pct/100)
m=lgb.LGBMClassifier(**P).fit(Xa,ya); ev("lgbm",m.predict_proba(Xb)[:,1])
pre=ColumnTransformer([("c",OneHotEncoder(handle_unknown="ignore"),CAT),("n",StandardScaler(),NUM)])
lr=make_pipeline(pre,LogisticRegression(C=0.5,max_iter=2000)).fit(Xa,ya); ev("logreg",lr.predict_proba(Xb)[:,1])
ev("blend",0.5*m.predict_proba(Xb)[:,1]+0.5*lr.predict_proba(Xb)[:,1])
# leakage demonstration: what happens if you keep the service columns
Xl=X.copy(); Xl["evt"]=d["last_service_event_type"].astype("category"); Xl["has_pickup"]=d["pickup_scheduled_at"].notna().astype(int)
ml=lgb.LGBMClassifier(**P).fit(Xl[~cut],ya); res["LEAKY_with_service_cols"]=dict(auc=round(roc_auc_score(yb,ml.predict_proba(Xl[cut])[:,1]),4)); print(res["LEAKY_with_service_cols"])
imp=pd.Series(m.booster_.feature_importance("gain"),X.columns).sort_values(ascending=False); print(imp.head(12).round(0))
json.dump(res,open("evidence/experiments.json","w"),indent=1)
