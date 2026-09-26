# 3-minute screen recording: outline (no slides)

**0:00–0:25 | What was asked, and the problem with it.** Open `email-thread.txt`, then `train.csv` in a terminal:
`python -c "import pandas as pd; print(pd.read_csv('data/train.csv').returned.mean())"` gives 0.11.
"Predicting 'no return' for everyone is already 89% accurate, so the 95% bar tells us nothing. I scored ranking (AUC) and rupees instead."

**0:25–1:05 | What I tried and threw away.**
- Show `src/experiment.py` output: with the service columns the model scores AUC 0.997. "`REVERSE_PICKUP` *is* the return. The test snapshot has none of these values, so I threw it away."
- Show `evidence/rolling_validation.csv`: LightGBM 0.767 vs logistic 0.779 on time-ordered folds. Threw away boosting and the blend.
- Show `evidence/ablation.txt`: 23 features down to 10, with no loss.

**1:05–1:35 | What I changed in the data.** In `src/features.py`: partner-feed duplicates removed, October values divided by 100 (show value ÷ list ≈ 92 for October), `000000` pincode appearing on every channel.

**1:35–2:15 | The decision.** Open `evidence/economics.csv`. Call the top 20% for +₹10.9k a month; holding the same orders gives −₹20k. "So I changed hold to call." Mention the Shield trade-off (46% of calls).

**2:15–2:50 | It runs.** `cd service && python -m uvicorn app:app`, open localhost:8000, score the demo order (72%, CALL, four reasons). Change payment to UPI and delivery to 3 days, rescore, and show the drop. Enter a bad SKU and show the polite error. Run `python -m pytest -q` (9 passed).

**2:50–3:00 | Close.** "Expect AUC about 0.78. Next step is a randomised call test to measure the 35% call effect."
