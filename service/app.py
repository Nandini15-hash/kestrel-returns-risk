"""Kestrel returns-risk service.  POST /score  with one order as JSON  ->  score, action, reasons.
GET / serves the one-page screen. No external API calls; runs offline."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import joblib, numpy as np, pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from features import build, CAT, NUM

try:
    BUNDLE = joblib.load(os.path.join(HERE, "model.joblib"))
except Exception as e:  # e.g. a different scikit-learn version
    sys.exit(f"Could not load service/model.joblib ({e}).\n"
             "Fix: pip install -r requirements.txt  (pins scikit-learn), or rebuild it with: python src/train.py")
MODEL, REF = BUNDLE["model"], BUNDLE["ref"]
PRODUCTS = pd.read_csv(os.path.join(HERE, "products.csv"))
CUST_PATH = os.path.join(HERE, "..", "data", "customers.csv")
CUSTOMERS = pd.read_csv(CUST_PATH) if os.path.exists(CUST_PATH) else None

app = FastAPI(title="Kestrel returns risk", version="1.0")


class Order(BaseModel):
    order_id: str = "NEW"
    order_placed_at: str = Field(..., examples=["2026-09-01 14:20"])
    customer_id: str = "UNKNOWN"
    sku: str = Field(..., examples=["KH-RV-03"])
    sales_channel: str = Field(..., examples=["marketplace"])
    payment_mode: str = Field(..., examples=["cod"])
    discount_pct: float = 0
    qty: int = 1
    order_value_inr: float = 0
    promised_delivery_days: int = 5
    delivery_pincode: str = "000000"
    is_gift: str = "N"
    customer_prior_orders: int = 0
    customer_prior_returns: int = 0
    delivery_note: str | None = None
    shield_member: str | None = None   # Y/N; looked up from customers.csv if omitted


def _label(feat, row):
    v = row[feat]
    if feat == "payment_mode": return "Cash on delivery" if v == "cod" else f"Paid by {str(v).replace('prepaid_', '').upper()}"
    if feat == "sales_channel": return f"Ordered via {str(v).replace('_', ' ')}"
    if feat == "family": return f"Product is a {v}"
    if feat == "discount_pct": return f"Discount of {v:.0f}%"
    if feat == "promised_delivery_days": return f"Delivery promised in {v} days"
    if feat == "is_gift": return "Marked as a gift" if v else "Not a gift"
    if feat == "customer_prior_orders": return f"Customer has {v} earlier order{'' if v == 1 else 's'}"
    if feat == "customer_prior_returns": return f"Customer has returned {v} earlier order{'' if v == 1 else 's'}"
    if feat == "prior_return_rate": return f"Customer's past return rate is {v:.0%}"
    if feat == "shield": return "Kestrel Shield member (free returns)" if v else "Not a Shield member"
    return feat


def explain(X, logit):
    """Reason = how much the log-odds move if this field were set to a typical value."""
    out = []
    for f in CAT + NUM:
        Xr = X.copy()
        if f in CAT:
            typical = REF["modes"][f]
            Xr[f] = pd.Categorical([typical])
        else:
            Xr[f] = REF["means"][f]
        p = MODEL.predict_proba(Xr)[:, 1][0]
        out.append((f, logit - np.log(p / (1 - p))))
    return out


@app.post("/score")
def score(o: Order):
    if o.sku not in set(PRODUCTS.sku):
        raise HTTPException(422, f"Unknown SKU '{o.sku}'. Known SKUs look like KH-AF-01 … KH-RH-03.")
    try:
        pd.to_datetime(o.order_placed_at)
    except Exception:
        raise HTTPException(422, "order_placed_at must look like 2026-09-01 14:20")
    rec = o.model_dump(); note = []
    shield = rec.pop("shield_member")
    cust = pd.DataFrame([{"customer_id": o.customer_id, "city": None, "state": None,
                          "signup_date": o.order_placed_at[:10], "shield_member": "N"}])
    if shield in ("Y", "N"):
        cust["shield_member"] = shield
    elif CUSTOMERS is not None and o.customer_id in set(CUSTOMERS.customer_id):
        cust = CUSTOMERS[CUSTOMERS.customer_id == o.customer_id]
    else:
        note.append("Shield status unknown - assumed not a member.")
    X, d = build(pd.DataFrame([rec]), cust, PRODUCTS)
    p = float(MODEL.predict_proba(X)[:, 1][0])
    logit = np.log(p / (1 - p))
    contrib = sorted(explain(X, logit), key=lambda t: -abs(t[1]))
    row = d.iloc[0]
    reasons = [{"reason": _label(f, row), "direction": "raises risk" if c > 0 else "lowers risk",
                "strength": round(float(abs(c)), 2)} for f, c in contrib if abs(c) >= 0.1][:4]
    call = p >= REF["call_cut"]
    return {
        "order_id": o.order_id,
        "return_probability": round(p, 3),
        "vs_average": f"{p / REF['base_rate']:.1f}x the average order",
        "action": "CALL customer before dispatch" if call else "Dispatch normally",
        "why_this_action": ("In the top 20% riskiest orders: a Rs 45 confirmation call is expected to save more than it costs."
                            if call else "Below the call threshold: a call would cost more than it is expected to save."),
        "reasons": reasons,
        "notes": note + ["This is a probability, not a verdict: about 7 in 10 flagged orders will NOT be returned. Do not hold or cancel on this score."],
    }


@app.get("/health")
def health():
    return {"ok": True, "model": "logistic regression, 10 inputs", "external_calls": 0}


@app.get("/")
def ui():
    return FileResponse(os.path.join(HERE, "index.html"))
