"""Turn out-of-fold scores into rupees. All costs from ops-policy v4.1 §4 and §7."""
import sys; sys.path.insert(0,"src")
import pandas as pd, numpy as np
from sklearn.metrics import accuracy_score
RETURN_COST=1150; CALL_COST=45; CALL_PREVENTS=0.35; HOLD_CANCEL=0.12
MARGIN_PCT=0.20   # ASSUMPTION: contribution lost when a good order is cancelled (not in the pack)
MONTHLY=700
o=pd.read_csv("evidence/oof_predictions.csv")
tr=pd.read_csv("data/train.csv").drop_duplicates("order_id"); pr=pd.read_csv("data/products.csv")
o=o.merge(tr[["order_id","order_value_inr","sku"]],on="order_id").merge(pr[["sku","list_price_inr"]],on="sku")
v=o.order_value_inr.where(o.order_value_inr/o.list_price_inr<10, o.order_value_inr/100)
n=len(o); scale=MONTHLY/n
rows=[]
for k in [0.02,0.05,0.10,0.15,0.20,0.25,0.30,0.40,0.50,0.60]:
    thr=o.p.quantile(1-k); f=o.p>=thr; R=o.y[f].sum(); N=(~o.y.astype(bool)&f).sum()
    call=CALL_PREVENTS*R*RETURN_COST-CALL_COST*f.sum()
    hold_best=HOLD_CANCEL*R*RETURN_COST                               # if a lost sale cost nothing
    hold=hold_best-HOLD_CANCEL*(v[f&(o.y==0)]*MARGIN_PCT).sum()
    rows.append(dict(flag_top=f"{int(k*100)}%",score_cut=round(thr,3),flagged_per_month=round(f.sum()*scale),
        precision=round(R/f.sum(),3),recall=round(R/o.y.sum(),3),accuracy_if_flag_means_return=round(((o.p>=thr)==o.y).mean(),3),
        call_net_rs_month=round(call*scale),hold_net_rs_month_best_case=round(hold_best*scale),hold_net_rs_month=round(hold*scale)))
t=pd.DataFrame(rows); print(t.to_string(index=False)); t.to_csv("evidence/economics.csv",index=False)
print("base rate",round(o.y.mean(),3),"accuracy of 'flag nothing'",round(1-o.y.mean(),3))
# per-order breakeven: call if P(return) > 45/(0.35*1150)
be=CALL_COST/(CALL_PREVENTS*RETURN_COST); f=o.p>=be; R=o.y[f].sum()
print(f"breakeven p={be:.3f}; flagged share={f.mean():.3f}; net/month=Rs{(CALL_PREVENTS*R*RETURN_COST-CALL_COST*f.sum())*scale:.0f}; returns prevented/month={CALL_PREVENTS*R*scale:.1f}")
print("returns/month at base rate", round(o.y.mean()*MONTHLY,1), "cost/month Rs", round(o.y.mean()*MONTHLY*RETURN_COST))
# at Ritu's Rs600
be6=CALL_COST/(CALL_PREVENTS*600); f6=o.p>=be6; print("at Rs600 breakeven",round(be6,3),"flag share",round(f6.mean(),3),"net/mo",round((0.35*o.y[f6].sum()*600-45*f6.sum())*scale))
# segments
o["flag"]=o.p>=be
for g in ["shield","family","payment"]:
    print(o.groupby(g).agg(n=("y","size"),rate=("y","mean"),flag_share=("flag","mean"),caught=("y",lambda s: o.flag[s.index][s==1].mean())).round(3))
# calibration
o["bin"]=pd.qcut(o.p,10,labels=False); print(o.groupby("bin").agg(pred=("p","mean"),actual=("y","mean"),n=("y","size")).round(3))
o.groupby("bin").agg(pred=("p","mean"),actual=("y","mean"),n=("y","size")).round(3).to_csv("evidence/calibration.csv")
