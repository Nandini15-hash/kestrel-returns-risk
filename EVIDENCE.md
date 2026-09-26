# Evidence that it works, and how often it doesn't

All numbers are reproducible with the scripts in `src/`. Raw outputs are in `evidence/`.

## 1. How it was tested

**Split:** rolling-origin, by order date. For each fold I train on every order before the cut and test on the next two months. There are four folds covering Nov 2025 to Jun 2026, 5,634 held-out orders in all, and no test order was seen in training. I tested this way because the hidden test set (Jul–Sep 2026) sits entirely after the training data, and a random split would flatter the model.

**Data used:** 10,504 unique orders (11,155 rows minus 651 duplicate partner-feed rows) and only fields that exist at dispatch.

| Fold (test months) | Orders | Return rate | ROC-AUC | PR-AUC |
|---|---|---|---|---|
| Nov–Dec 2025 | 1,382 | 10.4% | 0.769 | 0.37 |
| Jan–Feb 2026 | 1,383 | 12.0% | 0.786 | 0.45 |
| Mar–Apr 2026 | 1,448 | 11.5% | 0.775 | 0.37 |
| May–Jun 2026 | 1,421 | 11.3% | 0.787 | 0.41 |
| **Mean** | | 11.3% | **0.779 ± 0.009** | **0.40 ± 0.04** |

(Exact per-fold values for all three models are in `evidence/rolling_validation.csv`.)

**Models compared, on the same folds:**

| Model | ROC-AUC | PR-AUC | Kept? |
|---|---|---|---|
| Simple rule (past returns + discount) | 0.64 | 0.26 | Baseline only |
| Gradient boosting (LightGBM), same 10 features | 0.767 | 0.36 | Thrown away: worse and harder to explain |
| Logistic regression, all 23 features | 0.774 | 0.39 | Replaced by the lean version |
| **Logistic regression, 10 features** | **0.779** | **0.40** | **Shipped** |
| Blend of logistic and boosting | 0.778 | 0.39 | Thrown away: no gain |
| *Logistic + the two post-return service columns* | *0.997* | — | *Thrown away: leakage (see README)* |

**Ablation** (`evidence/ablation.txt`): removing payment mode (−0.031 AUC), Shield (−0.021), promised delivery days (−0.017) or prior returns (−0.012) hurts. Removing state, city, hour, weekday, month, pincode, product age, customer tenure, list price, order value, qty or delivery-note text costs nothing, so they were dropped.

## 2. How often it is wrong

**"Accuracy" is the wrong yardstick.** 11.3% of orders come back, so saying "no" to everything scores 88.7%. The best accuracy any cut-off reaches is 89.5%, flagging the top 2% of orders. 95% can't be reached with this data by this model or, very likely, any other: the information that decides most returns (changed mind, wrong model, damage in transit) doesn't exist at dispatch.

**At the recommended cut-off** (call the top 20%, score ≥ about 0.17), across the 5,634 held-out orders:

| | Actually returned | Not returned |
|---|---|---|
| **Flagged for a call** | 343 (caught) | 784 (false alarm) |
| **Not flagged** | 293 (missed) | 4,214 |

- Of the flagged orders, **30% are returned**, 2.7× the average. So **7 in 10 flagged orders would have been fine.** That's why the action is a ₹45 call, not a hold.
- Of all returns, **54% are in the flagged 20%**. The other 46% slip through.
- **Calibration** (`evidence/calibration.csv`): in each tenth of scores, the predicted rate is within about 2 points of the actual rate. For example, the top tenth predicts 40% and 42% come back. That means the score can be read directly as a probability, which is what the rupee maths relies on.

## 3. The kind of case it gets wrong

- **Missed returns look like ordinary orders.** Median score 0.09, no past returns, about 8% discount, 5-day delivery, mostly prepaid. They are spread across product families, with Room Heater slightly over-represented, probably seasonal remorse. Nothing visible at dispatch separates them.
- **False alarms are "risky-looking but fine" orders.** 61% are cash on delivery, 44% are Shield members, and they skew toward robot vacuums and water purifiers. These customers match the pattern of returners but keep the product.
- **Shield customers are over-flagged.** They are 22% of orders and 46% of calls. That's real (they return twice as often), but it matters for the service desk.
- **New customers** have no return history. The model then leans on payment mode and product, and its scores are less sharp.

## 4. Rupees at each cut-off (per month, 700 orders)

From `evidence/economics.csv`. Call: `0.35 × returns caught × ₹1,150 − ₹45 × calls`. Hold: `12% cancel × (returns caught × ₹1,150 − good orders × margin)`. The margin isn't in the pack; I assumed 20% of order value and also show a best case of zero lost margin.

| Flag top | Orders/mo | Share returned | Returns caught | **Call net ₹/mo** | Hold net ₹/mo (no lost margin) | Hold net ₹/mo (20% margin) |
|---|---|---|---|---|---|---|
| 5% | 35 | 54% | 24% | 6,075 | 2,623 | −2,244 |
| 10% | 70 | 42% | 37% | 8,749 | 4,081 | −7,618 |
| **20%** | **140** | **30%** | **54%** | **10,852** | 5,881 | **−20,072** |
| 30% | 210 | 25% | 66% | 11,555 | 7,201 | −33,539 |
| 40% | 280 | 21% | 74% | 10,952 | 8,076 | −46,467 |

Net savings from calls are flat between 20% and 40%. I recommend 20% because it's half the calling effort of 40% for the same money, and it stays positive if the return cost is really ₹600 (+₹2,648 a month). Leaving Shield members out of calls halves the gain to ₹5,330 a month.

## 5. The service

`tests/test_service.py`, 9 tests, all passing. They cover: health check, screen loads, a risky order gets a call, a safe order dispatches, the service never returns HOLD, unknown SKU / bad date / missing field each get a polite 422, and the endpoint's scores match `predictions.csv` for 20 test orders to within 0.001. Latency is about 55 ms per request on a laptop CPU, most of it spent computing the reasons.
