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
Price must be aligned with relevant moving averages (SMA 50 and 200).

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
The broad market environment influences the asset’s overall risk.

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

The system may suggest alternatives:

- Lower risk
- Better valuation
- Consistent with the user profile

**Note:** Alternatives **are not investment recommendations**, only relative comparisons.

---

## 10. Use of AI

The AI:

- receives only processed states and metrics
- never receives raw market data
- cannot issue orders or target prices
