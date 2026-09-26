"""Run: python -m pytest -q"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service"))
from fastapi.testclient import TestClient
from app import app
c = TestClient(app)
RISKY = {"order_placed_at": "2026-09-10 14:20", "sku": "KH-RV-03", "sales_channel": "marketplace", "payment_mode": "cod",
         "discount_pct": 25, "promised_delivery_days": 9, "customer_prior_orders": 3, "customer_prior_returns": 2, "shield_member": "Y"}
SAFE = {"order_placed_at": "2026-09-10 10:00", "sku": "KH-CF-01", "sales_channel": "app", "payment_mode": "prepaid_upi",
        "discount_pct": 3, "promised_delivery_days": 3, "customer_prior_orders": 5, "shield_member": "N"}

def test_health(): assert c.get("/health").json()["ok"]
def test_screen(): assert "Returns check" in c.get("/").text
def test_risky_gets_call():
    j = c.post("/score", json=RISKY).json()
    assert j["return_probability"] > 0.5 and j["action"].startswith("CALL") and j["reasons"]
def test_safe_dispatches():
    j = c.post("/score", json=SAFE).json()
    assert j["return_probability"] < 0.05 and j["action"] == "Dispatch normally"
def test_never_says_hold():
    for body in (RISKY, SAFE): assert "HOLD" not in c.post("/score", json=body).json()["action"].upper()
def test_bad_sku_is_polite():
    r = c.post("/score", json={**SAFE, "sku": "XX"}); assert r.status_code == 422 and "Unknown SKU" in r.json()["detail"]
def test_bad_date_is_polite():
    r = c.post("/score", json={**SAFE, "order_placed_at": "yesterday"}); assert r.status_code == 422
def test_missing_field():
    assert c.post("/score", json={"sku": "KH-CF-01"}).status_code == 422
import pytest
@pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'data', 'test_unlabelled.csv')), reason='client data not present')
def test_matches_batch_predictions():
    import pandas as pd
    te = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "test_unlabelled.csv")).head(20)
    pr = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "predictions.csv")).set_index("order_id")
    for _, r in te.iterrows():
        r = r.where(pd.notna(r), None)
        body = {k: r[k] for k in ["order_id","order_placed_at","customer_id","sku","sales_channel","payment_mode","discount_pct","qty",
                "order_value_inr","promised_delivery_days","is_gift","customer_prior_orders","customer_prior_returns","delivery_note"]}
        body["delivery_pincode"] = str(r["delivery_pincode"])
        j = c.post("/score", json=body).json()
        assert abs(j["return_probability"] - pr.loc[r.order_id, "score"]) < 1e-3
