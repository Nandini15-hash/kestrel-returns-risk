# Kestrel Home — Returns risk (Variant A)

Scores each order, before dispatch, for how likely it is to come back, and says what to do about it.

**Recommendation in one line:** don't hold orders. Call the riskiest 20% (about 140 a month) before dispatch. At policy costs that nets about **₹10,900 a month** (about ₹1.3 lakh a year). Holding the same orders loses money under any realistic margin. See `MEMO_TO_RITU.md`.

| File | What it is |
|---|---|
| `predictions.csv` | One score per `order_id` in `test_unlabelled.csv`. Higher means more likely to be returned. |
| `service/` | FastAPI endpoint (`POST /score`) and a one-page screen (`GET /`) |
| `EVIDENCE.md` | How it was validated, how often it's wrong, and what kind of order it gets wrong |
| `MEMO_TO_RITU.md` | One-page, non-technical memo |
| `submission-form.md` | The completed form |
| `RECORDING_SCRIPT.md` | Outline for the 3-minute walkthrough |
| `src/` | `features.py`, `model.py`, `train.py` (final model + predictions), `validate.py`, `ablate.py`, `economics.py`, `experiment.py` |
| `evidence/` | Every number quoted above, as CSV/JSON, plus a screenshot |

## Run it (clean machine, no API key needed)

You need Python 3.11 or newer.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate        macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cd service
python -m uvicorn app:app --port 8000
```

Open http://localhost:8000 and press **Check this order**.

The service ships with the trained model (`service/model.joblib`) and `service/products.csv`, so it starts without the client data. If `data/customers.csv` is present, it also looks up Shield status by `customer_id`. The service makes no calls to any external API, so there is nothing to pay for and nothing that can fail for lack of a key.

To call the endpoint directly:

```bash
curl -X POST localhost:8000/score -H "Content-Type: application/json" -d "{\"order_placed_at\":\"2026-09-10 14:20\",\"sku\":\"KH-RV-03\",\"sales_channel\":\"marketplace\",\"payment_mode\":\"cod\",\"discount_pct\":22,\"promised_delivery_days\":8,\"customer_prior_orders\":3,\"customer_prior_returns\":1}"
```

It returns `return_probability`, `action` (either "CALL customer before dispatch" or "Dispatch normally"), and up to four plain-English `reasons`. Bad input (an unknown SKU, an unreadable date, a missing field) gets a 422 with a readable message.

## Rebuild everything from the pack

Copy the pack's files into `data/` with their original names (`train.csv`, `test_unlabelled.csv`, `customers.csv`, `products.csv`, `sample_submission.csv`). Then:

```bash
python src/validate.py     # rolling time-split validation -> evidence/rolling_validation.csv, oof_predictions.csv
python src/economics.py    # rupees per threshold -> evidence/economics.csv, calibration.csv
python src/ablate.py       # feature ablation -> stdout (saved copy in evidence/ablation.txt)
python src/train.py        # final model -> predictions.csv and service/model.joblib
python -m pytest -q        # 9 tests: endpoint, polite errors, never says HOLD, API == batch scores
```

`data/` is git-ignored. The pack is client data (ops-policy §10), so keep this repository private.

## Decisions I made where the brief was unclear

1. **Dropped `last_service_event_type` and `pickup_scheduled_at`.** Both are written *after* a return is raised (policy §7), as of export day. In train, `REVERSE_PICKUP` means returned 100% of the time, and `INSTALL_DONE`/`DEMO_DONE` mean returned 0% of the time. At dispatch they don't exist yet: the test snapshot has only `NONE` or `INSTALL_BOOKED`, and no pickup times. Keeping them gives an AUC of 0.997 on paper and something close to useless in production.
2. **De-duplicated the 651 `partner_feed` rows.** Each one is an exact copy of a `crm` row, labels included. Left in, they double-weight partner orders and leak across validation folds.
3. **Fixed the October 2025 order values.** Every October row has value ÷ list price ≈ 92 instead of ≈ 0.92, so the new gateway stored paise. I divide those by 100. (The final model doesn't use value, but the rupee analysis does.)
4. **Validated on time, not at random.** Train on the past and test on the next two months, four times over. The hidden test is Jul–Sep 2026, after the whole training window.
5. **Replaced "95% accuracy" with ranking quality and rupees.** 11.3% of orders are returned, so a model that flags nothing is already 88.7% "accurate". The best accuracy any threshold reaches here is 89.5%. See `EVIDENCE.md`.
6. **Used the policy return cost of ₹1,150** (Finance's figure), not Ritu's ₹600, and checked that the recommendation still pays at ₹600. It does, though by less: about ₹2,600 a month.
7. **Recommended calls, not holds.** Policy §7 gives both effects: a call prevents 35% of returns on called orders, and a hold makes 12% of customers cancel. Arithmetic in the memo and `evidence/economics.csv`.
8. **Kept Shield members in scope.** Shield is the strongest single signal: 18.9% return rate against 9.3%. A courtesy call is much gentler on a high-value customer than a hold, which also addresses the service desk's concern. The alternative of excluding Shield is costed in `EVIDENCE.md`.
