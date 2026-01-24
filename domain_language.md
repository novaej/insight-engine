# Domain Language – Investment Insight MVP

This document defines the **common language** between business, technology, and AI.  
The terms defined here must be used consistently throughout the system.

---

## 1. User
A person who owns an investment portfolio and seeks to understand their current situation.

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

The portfolio is **persisted** after analysis. A single portfolio row is maintained (upserted on each analysis). Associated insights are stored with a foreign key link to the portfolio and replaced on re-analysis.

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
Comparable asset that, under current rules, presents a profile  
more aligned with the user.

---

## 14. Insight
Minimum unit of value delivered to the user.

An insight includes:
- asset state
- scenario
- horizon
- risks
- natural language explanation

---

## 15. Parabolic SAR
A trend-following indicator (Stop and Reverse) calculated using Wilder's algorithm. Used as a confirming signal for the SMA-based trend evaluation. When price is above SAR, the signal is bullish; when below, bearish. Parameters: initial AF = 0.02, step = 0.02, max AF = 0.20.

---

## 16. Translation
The process of converting AI-generated text (scenario, explanation, risks, summary) into the user's preferred language. Powered by Azure Translator. Specified via a `language` parameter (ISO code, e.g. `es`, `fr`, `pt`). English is the default and requires no translation.
