"""Feature engineering for Kestrel returns risk.
Only uses fields the warehouse has AT DISPATCH. Post-outcome fields are dropped."""
import re
import numpy as np
import pandas as pd

# Columns that are written AFTER the outcome (service system / logistics as of export day).
LEAKY = ["last_service_event_type", "pickup_scheduled_at"]
# Lean set chosen by ablation (evidence/ablation.txt). Dropping the rest cost nothing on rolling validation.
CAT = ["sales_channel", "payment_mode", "family"]
NUM = ["discount_pct", "promised_delivery_days", "is_gift", "customer_prior_orders",
       "customer_prior_returns", "prior_return_rate", "shield"]
EXTRA = ["tier", "state", "note_cat", "qty", "value_to_list", "pincode_missing", "warranty_months",
         "list_price_inr", "product_age_days", "tenure_days", "hour", "weekday", "month"]


def note_category(s):
    if not isinstance(s, str) or not s.strip():
        return "none"
    s = s.lower()
    if s.startswith("landmark"): return "landmark"
    if "neighbour" in s: return "neighbour"
    if "gate code" in s: return "gate_code"
    return re.sub(r"[^a-z]+", "_", s)[:30]


def clean_orders(df):
    """Data fixes: de-duplicate partner re-imports, rescale Oct-2025 paise values."""
    df = df.copy()
    if "source" in df:
        df = df.sort_values("source").drop_duplicates("order_id", keep="first")  # 'crm' sorts first
    return df


def build(df, customers, products):
    d = df.merge(customers, on="customer_id", how="left").merge(products, on="sku", how="left")
    t = pd.to_datetime(d["order_placed_at"])
    d["value_to_list"] = d["order_value_inr"] / (d["list_price_inr"] * d["qty"])
    # Oct-2025 festive orders were stored in paise by the new gateway (ratio ~ 92 instead of 0.92)
    d.loc[d["value_to_list"] > 10, "value_to_list"] /= 100
    d["pincode_missing"] = (d["delivery_pincode"].astype(str).str.lstrip("0") == "").astype(int)
    d["is_gift"] = (d["is_gift"] == "Y").astype(int)
    d["shield"] = (d["shield_member"] == "Y").astype(int)
    d["prior_return_rate"] = d["customer_prior_returns"] / d["customer_prior_orders"].clip(lower=1)
    d["tier"] = d["sku"].str[-2:]
    d["product_age_days"] = (t - pd.to_datetime(d["launch_date"])).dt.days
    d["tenure_days"] = (t - pd.to_datetime(d["signup_date"])).dt.days
    d["hour"], d["weekday"], d["month"] = t.dt.hour, t.dt.weekday, t.dt.month
    d["note_cat"] = d["delivery_note"].map(note_category)
    X = d[CAT + NUM].copy()
    for c in CAT:
        X[c] = X[c].astype(str).astype("category")
    return X, d
