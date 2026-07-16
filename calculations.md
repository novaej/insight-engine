# Metrics & Calculations Reference

This document explains every quantitative tool used by the analysis engine: what it
is in plain language, how it is computed, and how the business rules use it.
All calculations live in `insight_engine/services/metrics.py` and are pure,
deterministic math — no AI is involved at this layer.

Price data comes from Yahoo Finance: 2 years of daily history for the analyzed
asset, 1 year for the S&P 500 and for alternative candidates.

---

## 1. Simple Moving Average (SMA 50 / SMA 200)

**What it is:** The average closing price over the last N trading days. It smooths
out day-to-day noise so you can see the underlying direction of the price. A short
window (50 days ≈ 10 weeks) reacts quickly; a long window (200 days ≈ 10 months)
shows the long-term trend.

**How it's computed:** Sum of the last N daily closing prices, divided by N.
Returns nothing if there are fewer than N days of history.

**How it's used:** The trend rule compares the current price, SMA 50, and SMA 200:

- Price above both SMAs and SMA 50 above SMA 200 → bullish base signal
- Price below both SMAs and SMA 50 below SMA 200 → bearish base signal
- Anything in between → sideways

The classic intuition: when the 50-day average is above the 200-day average, recent
prices are stronger than the long-term norm (uptrend), and vice versa.

## 2. Parabolic SAR (Stop And Reverse)

**What it is:** A trend-following indicator invented by J. Welles Wilder. It draws a
series of dots that trail the price — below the price during an uptrend, above it
during a downtrend. When the price crosses the dots, the indicator "stops and
reverses," flipping to the other side. Think of it as a ratchet that follows the
trend and flags when the trend may have flipped.

**How it's computed** (standard Wilder algorithm):

- Each day: `SAR_today = SAR_yesterday + AF × (EP − SAR_yesterday)`
  - **EP (extreme point):** the highest high seen so far in an uptrend, or the
    lowest low in a downtrend.
  - **AF (acceleration factor):** starts at 0.02 and increases by 0.02 each time a
    new extreme is reached, capped at 0.20. The longer the trend runs, the faster
    the SAR catches up to the price.
- The SAR is clamped so it never moves inside the previous two days' range.
- If the price crosses the SAR, the trend reverses: the SAR jumps to the old EP and
  the AF resets to 0.02.

The engine keeps only the latest SAR value.

**How it's used:** As a confirmation layer on top of the SMA signal:

- SMA trend clear and SAR agrees (price above SAR = bullish, below = bearish) →
  confirmed trend
- SMA trend clear but SAR disagrees → downgraded to sideways (conflicting evidence)
- SMA says sideways → SAR breaks the tie
- SAR unavailable → SMA-only logic applies

## 3. Annualized Volatility

**What it is:** A measure of how much the price jumps around, expressed as a yearly
percentage. A volatility of 0.30 (30%) means the asset's yearly returns typically
swing about ±30% around their average. Higher volatility = bumpier ride.

**How it's computed:** Take the day-to-day percentage changes of the closing price,
compute their standard deviation, and multiply by √252 (252 = trading days in a
year) to scale the daily figure to an annual one. Requires at least 20 days of
history.

**How it's used:** Primary input to the risk dimension (low / medium / high) and to
the Profile Fit Score, where it is compared against per-risk-profile thresholds
(see `business_rules.md` §9.3).

## 4. Maximum Drawdown

**What it is:** The worst peak-to-trough loss over the period — "if you had bought
at the worst possible moment, how much would you have been down at the bottom?"
Expressed as a negative fraction: −0.25 means a 25% drop from the peak.

**How it's computed:** For every day, compare the price against the highest price
seen up to that day (`(price − running_max) / running_max`); take the most negative
value.

**How it's used:** Feeds the risk dimension, the Health Score drawdown component,
and the drawdown-tolerance check in the Profile Fit Score.

## 5. P/E Ratio and the "Historical Average" Benchmark

**What it is:** The price-to-earnings ratio — the price of the stock divided by its
earnings per share. Roughly: "how many years of current profits am I paying for?"
A high P/E means the market prices in a lot of future growth (or the stock is
expensive); a low P/E can mean a bargain or a business in trouble.

**How it's computed:** Taken directly from Yahoo Finance (`trailingPE`, falling back
to `forwardPE`).

**MVP caveat — the benchmark is a heuristic.** True historical P/E averages aren't
available from yfinance, so the "historical average" used by the valuation rule is
simply the mean of the trailing P/E (based on last year's actual earnings) and the
forward P/E (based on next year's expected earnings). If either is missing, the
benchmark is undefined and valuation comes back **inconclusive**.

**How it's used:** The valuation rule compares current P/E against this benchmark to
classify the asset as cheap, reasonable, or expensive.

## 6. Fundamental Metrics

All taken directly from Yahoo Finance company info; no local computation except
unit normalization.

- **Revenue growth** (`revenueGrowth`): year-over-year sales growth as a fraction
  (0.15 = 15%). Growing revenue is the most basic sign of a healthy business.
- **Profit margin** (`profitMargins`): what fraction of each dollar of sales
  becomes profit. Higher margins mean more pricing power and resilience.
- **Debt-to-equity** (`debtToEquity`): how much the company owes relative to what
  shareholders own. yfinance reports this as a percentage, so the engine divides
  by 100 (e.g. 150 → 1.5). High leverage amplifies both gains and trouble.

**How they're used:** Together they drive the fundamentals dimension
(strong / mixed / weak) per the thresholds in `business_rules.md` §4.3.

## 7. Market Context (S&P 500 vs its SMA 200)

**What it is:** A single yes/no reading of the overall market weather: is the S&P
500 index currently trading above its own 200-day moving average? Historically,
markets above their 200-day average are considered in a broad uptrend.

**How it's computed:** Fetch 1 year of S&P 500 (^GSPC) history, compute its SMA 200,
and compare the latest close against it.

**How it's used:** Classifies market context as favorable (above) or adverse
(below), which the synthesis rules combine with asset-level signals — e.g. high
risk + adverse context forces the `unattractive` state.

## 8. Derived Scores (built from the metrics above)

These are rule-layer composites, not raw metrics; full point tables live in
`business_rules.md` §9.

- **Health Score (0–100):** Weighted sum of trend, fundamentals, valuation, risk
  level, and max drawdown. Below 50 is one of the triggers for suggesting
  alternatives.
- **Profile Fit Score (0–100):** How well the asset's volatility, drawdown, and
  horizon match the user's risk profile. Also triggers alternatives below 50.

---

**Reading order if you're coming back cold:** this file for *what the numbers mean*,
`business_rules.md` for *how states are decided from them*, `domain_language.md`
for *terminology*.
