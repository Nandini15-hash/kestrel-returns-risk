# Submission form — Kestrel Home, Returns Risk (Variant A)

**GitHub repo URL:** https://github.com/Nandini15-hash/kestrel-returns-risk (private; access shared with the invitation address)

---

### What did you build, and what business decision does it support? State the number and the rupees.

A returns-risk scorer that runs at dispatch. It has a batch file (`predictions.csv`), an endpoint (`POST /score`) and a one-page screen that shows each order's chance of return, the action to take, and up to four plain-English reasons.

The decision it supports is **which orders get a ₹45 confirmation call before dispatch.** It doesn't support holding them. The riskiest 20% of orders (about 140 a month) contain 54% of all returns, and 30% of them come back against 11.3% on average. Calling them, at the policy's 35% prevention rate and ₹1,150 per return, nets about **+₹10,900 a month (about ₹1.3 lakh a year)**. Holding the same orders nets **−₹20,000 a month** at an assumed 20% margin on the 12% who cancel, and at best **+₹5,900** even if a lost sale cost nothing. I recommend calls, not holds.

### What score do you expect predictions.csv to get on the hidden outcomes, on which metric, and why that metric? Say how you estimated it.

**ROC-AUC ≈ 0.78, likely range 0.76–0.80.** Secondary: PR-AUC ≈ 0.40 (range 0.35–0.45), against a base rate of about 0.11.

**Why ROC-AUC:** the submission is a score where "higher means more likely", so what's being judged is ranking. The business action is also a ranking: call the top N. ROC-AUC measures exactly that, needs no threshold, and doesn't move with the return rate. Accuracy would reward predicting "no return" for everyone (88.7%). PR-AUC is the stricter view of the top of the list, so I report it too.

**How I estimated it:** rolling-origin validation on time. I trained on all orders before a cut and scored the next two months, over four folds (Nov 2025 to Jun 2026, 5,634 held-out orders). The fold AUCs were 0.769, 0.786, 0.775 and 0.787 (mean 0.779, SD 0.009). The hidden set is Jul–Sep 2026, 1–3 months after the final training data, which matches those folds. The range allows for fold variance, a 3-month horizon, and the test snapshot containing `INSTALL_BOOKED`, a value that never appears in train. That column is excluded, so it shouldn't matter, but it is a sign the snapshot differs.

### How do you know it works? How you validated, on what split, error rate, and the kind of case it gets wrong.

- **Split:** time-based rolling origin (above), never random. There were no duplicate orders across folds: I removed the 651 partner-feed copies first.
- **Leakage check:** with the two service-system columns left in, AUC is 0.997. `REVERSE_PICKUP` means returned 100% of the time and `INSTALL_DONE`/`DEMO_DONE` 0%. They are written after the outcome, so I dropped them. The 0.78 is what's left using dispatch-time fields only.
- **Error rate at the recommended cut-off (top 20%):** 343 caught, 784 false alarms, 293 missed, 4,214 correct passes. **Precision 30%** (7 in 10 flagged orders are fine), **recall 54%**. Best accuracy at any threshold is 89.5%, against 88.7% for predicting nobody returns.
- **Calibration:** in each decile of scores, predicted and actual rates are within about 2 points (top decile: 40% predicted, 42% actual). Scores can be used as probabilities in the rupee maths.
- **What it gets wrong:** (a) missed returns look like ordinary orders: prepaid, no return history, modest discount, normal delivery promise. Nothing visible at dispatch separates them. (b) False alarms are "risky-looking but kept": 61% COD, 44% Shield, skewed toward robot vacuums and purifiers. (c) New customers get less sharp scores because they have no return history.
- **Service:** 9 pytest tests, including that the API score equals the batch score for the same order and that the service never outputs "hold". Details in `EVIDENCE.md`.

### Did you change, narrow, or push back on the client's ask? What, when, and why.

Yes, on three points, all decided after the data exploration and the policy read, before modelling:

1. **"95% accuracy":** pushed back. The base rate makes 88.7% free, and 89.5% is the ceiling here. I replaced it with ranking quality (AUC) and rupees, and gave the board a sentence it can defend: "the riskiest fifth of orders holds over half our returns."
2. **"Hold dispatch on anything it flags":** changed to "call before dispatch". With policy §7 figures (12% cancellation on holds, 35% prevention from calls) and 7 in 10 flagged orders being fine, holds lose money and calls make it. Farhan asked for exactly this comparison.
3. **Return cost:** used Finance's policy figure, ₹1,150, not ₹600, and showed the recommendation survives at ₹600 (+₹2,600 a month).
4. **"We'll deal with Shield later":** didn't defer it. Shield is the second-strongest signal and 46% of flagged orders, so it can't be left for later. Calls rather than holds addresses the service desk's concern. The option of excluding Shield is costed (+₹5,300 a month).

### What is wrong with what you are handing us, or with the data we handed you?

**Data:**
- `last_service_event_type` and `pickup_scheduled_at` are post-outcome leakage as of export day (policy §7). The test file shows what dispatch really looks like: only `NONE`/`INSTALL_BOOKED`, zero pickup dates. `INSTALL_BOOKED` never appears in train at all.
- 651 `partner_feed` rows are exact duplicates of `crm` rows (same `order_id`, same label).
- **All 700 October 2025 orders have `order_value_inr` about 100× too high** (value ÷ list price ≈ 92, not 0.92). The new gateway stored paise. Fixed by ÷100.
- Pincode `000000` is supposed to be walk-in partner orders only, but it appears on 848 unique orders across **all** channels (app 300, marketplace 238, web 218, partner 92).
- Policy §9 says the `source` column shows legacy Zoho vs CRM, but it only contains `crm`/`partner_feed`. I couldn't identify legacy rows, so the UTC-not-IST timestamp issue can't be corrected. It only affects event and pickup times, which I don't use.
- `customer_prior_returns` matches the returns visible in this export for only about 83% of rows. The rest presumably reflect history before April 2025. I trusted it, because it isn't correlated with the order's own outcome in a way that suggests leakage, but it's the model's strongest feature, so it's worth confirming how it's computed at dispatch.
- About 1.1% of non-returned orders have a pickup booked (booked, then cancelled, per §7).

**My submission:**
- The ₹ figures depend on the spring pilot's 35% prevention rate, which comes from a small, non-randomised pilot. That's why the memo proposes a randomised test.
- The margin lost on a cancelled order (20%) is my assumption. It isn't in the pack.
- Reasons are "what if this field were typical" changes in the model's log-odds. That makes them a faithful description of this model, but not causal.
- The model is logistic regression with no interactions. Gradient boosting didn't beat it here, but with more data it might.
- `service/model.joblib` is tied to scikit-learn 1.8.0 (pinned). With another version, the service stops with a message telling you to reinstall or retrain.
- The screen has no login. It's meant for an internal network.

### What does one prediction cost, and what would a month cost at Kestrel's volume (about 700 orders a month)?

**No paid calls. The product uses no model API.**
- Per prediction: about 55 ms on a laptop CPU. On a ₹0 existing machine, marginal cost is ₹0. Even on a dedicated small cloud VM at about ₹700 a month, that's ₹700 ÷ 700 = **₹1 per prediction**, all of it fixed cost that doesn't scale per order.
- A month at 700 orders: **₹0** on existing hardware, or **about ₹700** for a dedicated VM.
- The action it triggers does cost money: 140 calls × ₹45 = **₹6,300 a month**. That is covered by about ₹17,150 of returns avoided.

### What did you deliberately leave out, and why that rather than something else?

- **An LLM in the product.** Reasons come straight from the model. An LLM would add a per-order bill (Farhan asked for none), a failure mode, and no accuracy.
- **Delivery-note text, location, time of day, product age, customer tenure.** Ablation showed each added nothing (±0.002 AUC), so fewer inputs means fewer things that can break at dispatch.
- **Hyperparameter search and larger models.** The gap between logistic regression and boosting was about 0.01 AUC in favour of the simpler model. Time went into leakage, data fixes and rupees instead, which move the decision more.
- **Auth, a database, Docker.** "A small thing that runs" was the brief.

### Anything you built or found that nobody asked for?

- The **hold-vs-call rupee table** at every cut-off (`evidence/economics.csv`), which is what Farhan asked for in the thread.
- A **leakage demonstration** (0.997 AUC with the service columns), useful for showing why that column set must never be used.
- The **October paise bug**, the duplicate partner feed, and the `000000` pincode appearing on every channel. These affect Kestrel's reporting, not just this model.
- A **randomised call-test design** for next week, so the 35% effect gets measured rather than assumed.
- A test that the **API and the batch file agree**, so the screen can never show a different score from the one scored here.

### What did you use AI for? Which tools and models, where they helped, where they misled you, what you threw away. Link your three-minute screen recording here.

**Tool:** Claude (Anthropic), in the Claude desktop app's Cowork mode, working as an agent with access to the pack on my machine. **Claude did almost all of the work:** data exploration, finding the data problems, feature engineering, validation, the model, the rupee analysis, the FastAPI service and screen, the tests, the memo, the evidence write-up and the first draft of this form. **My part:** giving it the pack and the brief, running the service and tests on my own Windows machine to confirm they work on a clean setup, creating the private repo and pushing, recording the walkthrough, and choosing what to submit. I'm stating this plainly because it's what happened.

**No AI inside the product.** The service is a logistic regression with no API calls, so it costs ₹0 per prediction and needs no key.

**Cost:** covered by my existing Claude subscription, with ₹0 of separate API spend.

**Where it helped:** it checked every column against the ops policy and the email thread and found the leakage (`REVERSE_PICKUP` = 100% returned), the October paise bug, the 651 duplicate partner-feed rows and the `000000` pincode appearing on every channel. It also pushed back on "95% accuracy" and "hold", using the policy's own costs.

**Where it went wrong and had to correct itself:** the first "reasons" code compared categorical fields against a blank value (caught from a pandas warning, then fixed). It started with 23 features, and ablation cut that to 10. A draft evidence table briefly held numbers from an older run and was re-checked against the output files. On my machine, the service had to be restarted to pick up `customers.csv`, and a PowerShell quoting issue broke the curl demo, so it switched to `Invoke-RestMethod`.

**Thrown away:** LightGBM (AUC 0.767 vs 0.779), a logistic/LightGBM blend (no gain), the 23-feature model, and the model using the service-system columns (AUC 0.997, but leaky).

**Recording:** `<link>`

**Public Google Drive link:** `<link>` (recording only — no data files)

### Someone picks this up on Monday and you are unreachable. The three things they need to know.

1. **Never add `last_service_event_type` or `pickup_scheduled_at` as features.** They are written after a return starts, and they make the model look perfect while being useless at dispatch. Also de-duplicate `partner_feed` rows and divide October 2025 order values by 100 before any analysis (`src/features.py` does both).
2. **The action is a call, not a hold, and every rupee depends on the 35% call-effect figure.** Run the randomised call test (call half of each day's flagged orders) and re-run `src/economics.py` with the measured effect after 6–8 weeks.
3. **To retrain:** put the new export in `data/`, run `python src/validate.py`, then `python src/train.py`, then `python -m pytest -q`. If rolling AUC drops below about 0.74, or the top-20% share returned drops below about 20%, stop calling on the score and investigate. Start the service with `cd service && python -m uvicorn app:app`.
