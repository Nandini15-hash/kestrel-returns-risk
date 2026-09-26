# Memo — Returns risk

**To:** Ritu Deshpande, Head of D2C Operations  **Cc:** Farhan Sheikh, Meenal Joshi, Tanmay Kulkarni
**Re:** What the returns model can do, and what to do with it

## The decision

**Don't hold orders. Call the riskiest one in five before dispatch.**

The model is built and it works. It can't do what we promised the board, and holding flagged orders would cost more than it saves. Using it to trigger a ₹45 confirmation call does pay.

## The number

- About **11 in every 100 orders** come back. A "model" that predicts nothing ever comes back is right 89% of the time, so **95% accuracy isn't a meaningful target**, and nothing we tested gets near it. The information that decides most returns (a change of mind, the wrong model, transit damage) doesn't exist yet when we dispatch.
- What the model *does* do well is **rank orders by risk**. Among the riskiest 20% of orders, **3 in 10 come back**, nearly three times the average. That 20% contains **over half of all returns**. We tested this honestly: trained on older months, checked on later months it had never seen, four times over.
- **7 in 10 flagged orders would have been fine.** That is why a flag should trigger a call, not a hold.

I suggest we tell the board this instead: *"We now know in advance which fifth of orders produces over half our returns, and we act on it."* It's true, measurable, and we can track it every month.

## The rupees (at about 700 orders a month, using the policy cost of ₹1,150 per return)

| | Per month |
|---|---|
| What returns cost us today (about 79 returns) | about ₹91,000 |
| **Call the top 20%** (about 140 calls × ₹45 = ₹6,300; prevents about 15 returns = ₹17,150) | **+₹10,900 saved** (about ₹1.3 lakh a year) |
| Hold the same 140 orders instead (12% of customers cancel, about 12 of them good sales) | **−₹20,000** if a lost sale costs us 20% of its value. Even if a lost sale cost nothing, a hold saves only ₹5,900, half what a call saves. |

If the true cost of a return is closer to your ₹600, calls still come out ahead, at about ₹2,600 a month. Holds never do.

This isn't the whole returns problem. It's a cheap, safe first cut at it, about 12% of the cost. The bigger levers are cash on delivery, long delivery promises, and Shield returns policy.

## What to do next week

1. **Stop the hold plan.** Tell the warehouse no order is held on a model score.
2. **Start calls on the top 20%, as a proper test.** Each day, call a random half of the flagged orders and leave the other half alone. After 6–8 weeks we'll know whether the spring pilot's "35% of returns prevented" holds up. Every rupee above depends on it.
3. **Call Shield members too, but as a courtesy call.** They return twice as often and make up nearly half of the flagged orders. A friendly "confirming your order" call protects the relationship; a hold wouldn't. If Meenal would rather exclude them, the saving halves to about ₹5,300 a month.
4. **Ask Tanmay for three data fixes.** October order values were stored ×100 by the new payment gateway. Partner-outlet orders appear twice. About 850 orders from every channel, not just walk-ins, have the blank "000000" pincode.
5. **Confirm with Farhan** what a cancelled sale costs us (margin). It's the one number I had to assume.

Running cost: **₹0 a month** in software. The model runs on any laptop or server we already have, with no paid AI service and no per-order bill.
