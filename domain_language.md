# Domain Language – Investment Insight MVP

This document defines the **common language** between business, technology, and AI.  
The terms defined here must be used consistently throughout the system.

---

## 1. User
A person who owns an investment portfolio and seeks to understand their current situation.

Users are registered accounts (email + password). API access requires a bearer
token obtained on login; each user owns exactly one portfolio.

---

## 2. User Profile

Defines the context for the analysis.

- **Risk:** low | moderate | high  
- **Horizon:** short | medium | long  
- **Objective:** growth | income | capital_protection

The profile **modulates** the interpretation, not the base rules.

---

## 3. Asset
An individual financial instrument.

Types supported in the MVP:  
- Stock  
- ETF

---

## 4. Portfolio
A set of assets with defined quantities.
The portfolio is analyzed:
- as the sum of its parts
- as a global risk structure

The portfolio is **persisted** and belongs to a user. Its holdings are stored as
purchase lots (see 4b). Associated insights are stored with a foreign key link to
the portfolio and are **kept across re-analyses** — older insights form the
queryable history.

---

## 4b. Position (Purchase Lot)

One purchase of a ticker: quantity, optional purchase price, and optional
purchase date. A ticker may have several lots at different prices. For analysis,
lots are aggregated per ticker (summed quantity, quantity-weighted average
cost). Max 20 distinct tickers per portfolio.

---

## 5. Trend
Indicates whether the market is supporting the asset's price.

Values:
- bullish
- sideways
- bearish

Determined by SMA 50/200 alignment and confirmed/moderated by Parabolic SAR when available.

---

## 6. Valuation
Relationship between current price and historical fundamentals.

Values:  
- cheap  
- reasonable  
- expensive  
- inconclusive

---

## 7. Fundamentals
Underlying quality of the business.

Values:  
- strong  
- mixed  
- weak

---

## 8. Risk / Volatility
Magnitude of potential declines and abrupt movements.

Values:  
- low  
- medium  
- high

---

## 9. Market Context
General environment of the financial market.

Values:  
- favorable  
- adverse

---

## 10. Asset State
Final result from the combination of rules.

Values:  
- healthy  
- healthy but expensive  
- neutral  
- risky  
- unattractive

---

## 11. Scenario
Narrative description of the asset’s most likely behavior,  
without price predictions or timing.

---

## 12. Main Risk
Factor that could negatively affect the asset or portfolio.

Examples:  
- valuation correction  
- macroeconomic risk  
- high volatility

---

## 13. Alternative
Comparable asset that, under current rules, presents a profile more aligned with the user. Alternatives are triggered deterministically (scores and news flags) and are never investment recommendations.

Candidates (AI-proposed, with the config universe as fallback) are validated
with real metrics and must pass the user's risk-tolerance thresholds, have a
profile fit score of at least 50, and not already be held in the portfolio.

---

## 14. Portfolio Role
Classification of an asset's function within a portfolio.

Values:
- US_LARGE_CAP_CORE
- GROWTH_TECH
- DIVIDEND_INCOME
- DEFENSIVE
- EMERGING_MARKETS
- BONDS_STABILITY

Used to find comparable candidates when alternatives are triggered.

---

## 15. Health Score
A 0–100 score measuring the overall quality of an asset's current state, derived from trend, fundamentals, valuation, risk level, and drawdown.

---

## 16. Profile Fit Score
A 0–100 score measuring how well an asset aligns with the user's risk profile, considering volatility tolerance, drawdown tolerance, and horizon alignment.

---

## 17. News Flags
Binary risk signals extracted from recent news headlines via keyword matching (no AI). Four flags: regulatory_risk, earnings_negative, management_change, litigation_risk.

---

## 18. Insight
Minimum unit of value delivered to the user.

An insight includes:
- asset state
- scenario
- horizon
- risks
- natural language explanation
- portfolio role (optional)
- health score (optional)
- profile fit score (optional)
- alternatives (optional, when triggered)
- position context (optional: market value, portfolio weight, average cost,
  unrealized gain/loss — when analyzed as part of a portfolio)
- analysis timestamp (insights accumulate; history is queryable per ticker)

---

## 18b. Concentration

Portfolio-level state derived from position weights: `concentrated` when any
single position exceeds 25% of portfolio value or any portfolio role exceeds
40% combined; otherwise `diversified`. A classification, not an instruction.

---

## 19. Parabolic SAR
A trend-following indicator (Stop and Reverse) calculated using Wilder's algorithm. Used as a confirming signal for the SMA-based trend evaluation. When price is above SAR, the signal is bullish; when below, bearish. Parameters: initial AF = 0.02, step = 0.02, max AF = 0.20.

---

## 20. Translation
The process of converting AI-generated text (scenario, explanation, risks, summary) into the user's preferred language. Powered by Azure Translator. Specified via a `language` parameter (ISO code, e.g. `es`, `fr`, `pt`). English is the default and requires no translation.
