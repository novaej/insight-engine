# Business Rules – Investment Insight MVP

## 1. System Purpose
This system provides **educational and contextual analysis** of financial investments (stocks and ETFs), aimed at non-expert users.

The system **does NOT** offer financial advice, buy/sell signals, or price predictions. Its goal is to help users **understand their portfolio and current risks**.

---

## 2. Core Principles

1. Rules **classify states**, they do not give orders.
2. Every output must be expressed as:
   - state
   - likely scenario
   - risks
3. A time horizon must always be specified.
4. Maximum of 3 signals or risks per insight.
5. If there is insufficient clarity → state `neutral`.
6. In case of conflicting signals → prioritize the most conservative signal.
7. The AI **does not decide**, it only explains.

---

## 3. Analysis Dimensions

Each asset is evaluated using **five independent dimensions**:

1. Trend
2. Valuation
3. Fundamentals
4. Risk / Volatility
5. Market context

Each dimension produces **a single discrete state**.

---

## 4. Rules by Dimension

### 4.1 Trend
- Bullish
- Sideways
- Bearish

**General rule:**
Price alignment with moving averages (SMA 50 and 200) determines the base trend signal. The Parabolic SAR acts as a confirming or tie-breaking indicator:

- If SMA trend is clear (bullish or bearish) and SAR agrees → confirmed trend.
- If SMA trend is clear but SAR disagrees → sideways (conflict).
- If SMA trend is sideways and SAR is available → SAR provides direction.
- If SAR is unavailable → SMA-only logic applies.

---

### 4.2 Valuation
- Cheap
- Reasonable
- Expensive
- Inconclusive

**General rule:**  
Compare current multiples with historical or sector averages.

---

### 4.3 Fundamentals
- Strong
- Mixed
- Weak

**General rule:**  
Business strength is determined by growth, margins, and debt levels.

---

### 4.4 Risk / Volatility
- Low
- Medium
- High

**General rule:**  
Historical drawdowns and volatility determine the risk level.

---

### 4.5 Market Context
- Favorable
- Adverse

**General rule:**  
Each asset is judged against its **role benchmark index** (configured in
`config/benchmarks.json`): US_LARGE_CAP_CORE → ^GSPC, GROWTH_TECH → QQQ,
DIVIDEND_INCOME → VYM, DEFENSIVE → XLP, EMERGING_MARKETS → EEM,
BONDS_STABILITY → AGG.

- Benchmark above its 200-day SMA → favorable
- Benchmark below its 200-day SMA → adverse
- Benchmark data unavailable → favorable by default; the missing signal remains
  visible (`benchmark_above_sma200: null`) so consumers can tell the default was
  applied. There is **no** S&P 500 fallback — the S&P is only used when it *is*
  the asset's role benchmark.

The benchmark ticker used is always exposed in the insight's metrics
(`benchmark_ticker`) for transparency.

---

## 5. Final State Synthesis

**Possible asset states:**
- `healthy`
- `healthy_but_expensive`
- `neutral`
- `risky`
- `unattractive`

**Combination rules:**
- Two or more negative signals → do not force a positive state.
- High risk + adverse context → `unattractive`.
- Weak fundamentals → `risky` regardless of other signals.

---

## 6. Recommended Horizon

The system suggests an indicative horizon:

- short-term
- medium-term
- long-term
- not currently recommended

**Note:** The horizon does **not imply action**, it only provides temporal context.

---

## 7. Likely Scenarios

Scenarios describe **what could happen**, not what will happen.

**Examples:**
- Moderate gains with corrections
- Sideways movement with volatility
- Continued downward pressure

---

## 8. Main Risks

Each insight should list **a maximum of 3 risks**, derived mechanically from the rules.

**Examples:**
- High valuation
- Adverse macro context
- High volatility

---

## 9. Alternatives

The system suggests 1–3 alternative assets when the current asset scores poorly or presents news-driven risks. Alternatives are **not investment recommendations**, only relative comparisons based on deterministic rules.

### 9.1 Portfolio Role Classification

Each asset is classified into a **portfolio role** used to find comparable candidates:

| Role | Classification Logic |
|------|---------------------|
| `US_LARGE_CAP_CORE` | Large blend ETFs, S&P 500 ETFs, stocks with marketCap > $50B in non-specialized sectors |
| `GROWTH_TECH` | Technology/growth ETFs, stocks in Technology or Communication Services sectors |
| `DIVIDEND_INCOME` | Dividend/income/yield ETFs, stocks with dividendYield > 3% |
| `DEFENSIVE` | Utilities/consumer defensive/health ETFs, stocks in Utilities/Consumer Defensive/Healthcare |
| `EMERGING_MARKETS` | Emerging/developing market ETFs |
| `BONDS_STABILITY` | Bond/fixed income/treasury ETFs |

- ETFs are classified by `category` keyword matching, then `fundFamily` fallback.
- Stocks are classified by `sector`, then `dividendYield`, then `marketCap`.
- Default fallback: `US_LARGE_CAP_CORE`.

### 9.2 Health Score (0–100)

Measures the overall quality of an asset's current state:

| Component | Values | Points |
|-----------|--------|--------|
| Trend | bullish=25, sideways=15, bearish=0 | /25 |
| Fundamentals | strong=25, mixed=15, weak=0 | /25 |
| Valuation | cheap=20, reasonable=15, expensive=5, inconclusive=10 | /20 |
| Risk Level | low=15, medium=10, high=0 | /15 |
| Drawdown | > -15%: 15, > -30%: 8, else: 0 | /15 |

**Penalty:** If `debt_to_equity > 2.0`, subtract 5 points (floor at 0).

### 9.3 Profile Fit Score (0–100)

Measures alignment between the asset and the user's risk profile:

| Component | Logic | Points |
|-----------|-------|--------|
| Volatility alignment | annualized_volatility ≤ threshold: 40; ≤ 1.5× threshold: 20; else: 0 | /40 |
| Drawdown alignment | max_drawdown ≥ threshold: 30; ≥ 1.5× threshold: 15; else: 0 | /30 |
| Horizon alignment | match=30, adjacent=15, mismatch or not_recommended=0 | /30 |

**Volatility thresholds by risk profile:**
- low: 15%
- moderate: 25%
- high: 40%

**Drawdown thresholds by risk profile:**
- low: -10%
- moderate: -20%
- high: -35%

### 9.4 News Risk Flags

Binary flags extracted from recent news headlines via keyword matching (no AI):

| Flag | Keywords |
|------|----------|
| `regulatory_risk` | regulatory, regulation, sec, antitrust, fine, fined, compliance, sanctions, investigation, probe, subpoena |
| `earnings_negative` | misses, missed, disappoints, downgrade, loss, losses, decline, slump, warning, profit warning, revenue miss, below expectations, guidance cut |
| `management_change` | ceo resign, ceo steps down, ceo fired, ceo departure, cfo resign, cfo steps down, management shakeup, executive leaves, leadership change, board ousts |
| `litigation_risk` | lawsuit, sued, litigation, class action, settlement, legal action, court ruling, damages, plaintiff, defendant |

All headline titles are lowercased and concatenated for matching.

### 9.5 Trigger Conditions

Alternatives are triggered when **any** of these conditions are met:
- Health score < 50
- Profile fit score < 50
- Any news risk flag is `True`

### 9.6 Candidate Selection and Filtering

**Candidate sources (fallback chain):**
1. **AI-driven** (`use_ai=True`): The LLM suggests 3–5 candidates in the same portfolio role; each candidate is then validated with real market metrics.
2. **JSON fallback**: Static `config/candidate_universe.json` mapping from role → ticker list. Used when `use_ai=False`, when the AI fails, **or when every AI candidate was filtered out** — a trigger should not produce an empty list if the config has viable candidates.

**Hard filters (exclude candidate if):**
- `annualized_volatility` > user's risk threshold
- `max_drawdown` < user's drawdown threshold (more negative)
- `profile_fit_score` < 50 — an alternative must fit the user's profile at least as well as the threshold that triggers alternatives; otherwise the system would suggest assets it flags elsewhere
- ticker is **already held in the portfolio** (something you own is not an alternative)

**Ranking:** By health score descending.

**Output:** Top 3 candidates after filtering, each carrying its health score and profile fit score.

---

## 9b. Position-Aware Portfolio Rules

Deterministic rules over the user's actual holdings (purchase lots aggregated
per ticker). Like all rules, they classify states — they never produce buy/sell
language. A paper loss yields *context*, not advice.

### 9b.1 Position Weights

- Market value per ticker = aggregated quantity × current price.
- Weight = market value / total portfolio value.
- Positions without a current price get no weight and are excluded from the total.

### 9b.2 Unrealized Gain/Loss

- `(current_price − avg_purchase_price) / avg_purchase_price`, where the average
  purchase price is the quantity-weighted mean over the ticker's lots.
- Undefined (null) when no lot has a purchase price.

### 9b.3 Concentration

| Check | Threshold | Effect |
|-------|-----------|--------|
| Single position weight | > 25% | ticker flagged |
| Combined portfolio-role weight | > 40% | role flagged |

Any flag → portfolio concentration state `concentrated`; otherwise `diversified`.

### 9b.4 Value-Weighted Overall Risk

Portfolio risk is weighted by position value instead of counting assets:

- Combined weight of assets in `risky`/`unattractive` states > 50% → high
- > 0% → medium
- 0% → low
- No weights available (e.g. all prices missing) → fall back to count-based logic.

Position and portfolio context (weights, unrealized gain/loss, concentration
state) are passed to the AI for explanation, subject to the same
non-prescriptive constraints.

---

## 10. Use of AI

The AI:

- receives only processed states and metrics
- never receives raw market data
- cannot issue orders or target prices

---

## 11. Translation

AI-generated text fields (scenario, explanation, risks, and portfolio summary) can be translated into any supported language via Azure Translator. Translation is applied only when a `language` parameter is provided and the target language is not English. If translation is unavailable, the original English text is returned unchanged.
