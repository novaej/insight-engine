SYSTEM_PROMPT = """You are an educational investment analysis assistant. Your role is to explain \
the current state of an asset in clear, accessible language for non-expert investors.

STRICT RULES:
- NEVER provide buy/sell signals or recommendations
- NEVER predict specific prices or timing
- NEVER use imperative language ("you should", "buy", "sell", "hold")
- Always explain in educational and contextual terms
- Maximum 3 risks per insight
- Always include a time horizon context
- Use plain language, avoid jargon where possible

Your output must be factual, balanced, and help the user understand their position."""

INSIGHT_PROMPT_TEMPLATE = """\
Analyze the following asset state and provide an educational explanation.

Ticker: {ticker}
Asset State: {asset_state}
Trend: {trend}
Valuation: {valuation}
Fundamentals: {fundamentals}
Risk Level: {risk_level}
Market Context: {market_context}
Horizon: {horizon}

Key Metrics:
- Current Price: {current_price}
- SMA 50: {sma_50}
- SMA 200: {sma_200}
- P/E Ratio: {pe_ratio}
- Revenue Growth: {revenue_growth}
- Profit Margin: {profit_margin}
- Debt/Equity: {debt_to_equity}
- Volatility (annualized): {volatility}
- Max Drawdown: {max_drawdown}

{user_context}

Provide your response in the following JSON format:
{{
  "scenario": "A 1-2 sentence description of the most likely scenario without price predictions",
  "risks": ["risk1", "risk2", "risk3"],
  "explanation": "A 3-5 sentence educational explanation of what this means for the investor"
}}"""

INSIGHT_WITH_ALTERNATIVES_PROMPT_TEMPLATE = """\
Analyze the following asset state and provide an educational explanation.
Additionally, suggest alternative assets that may better fit the investor's profile.

Ticker: {ticker}
Asset State: {asset_state}
Trend: {trend}
Valuation: {valuation}
Fundamentals: {fundamentals}
Risk Level: {risk_level}
Market Context: {market_context}
Horizon: {horizon}

Key Metrics:
- Current Price: {current_price}
- SMA 50: {sma_50}
- SMA 200: {sma_200}
- P/E Ratio: {pe_ratio}
- Revenue Growth: {revenue_growth}
- Profit Margin: {profit_margin}
- Debt/Equity: {debt_to_equity}
- Volatility (annualized): {volatility}
- Max Drawdown: {max_drawdown}

{user_context}

Alternatives Context:
- Health Score: {health_score}/100
- Profile Fit Score: {profile_fit_score}/100
- Portfolio Role: {portfolio_role}
- Trigger Reasons: {trigger_reasons}
{news_flags_context}

Suggest 3-5 alternative tickers in the same portfolio role that may be more suitable.
For each alternative, provide a one-line educational reason (not a recommendation).
NEVER use prescriptive language—describe characteristics, not actions.

Provide your response in the following JSON format:
{{
  "scenario": "A 1-2 sentence description of the most likely scenario without price predictions",
  "risks": ["risk1", "risk2", "risk3"],
  "explanation": "A 3-5 sentence educational explanation of what this means for the investor",
  "alternatives": [
    {{"ticker": "TICKER1", "reason": "One-line educational reason"}},
    {{"ticker": "TICKER2", "reason": "One-line educational reason"}}
  ]
}}"""


BATCH_ASSET_BLOCK_TEMPLATE = """\
Ticker: {ticker}
Asset State: {asset_state}
Trend: {trend}
Valuation: {valuation}
Fundamentals: {fundamentals}
Risk Level: {risk_level}
Market Context: {market_context}
Horizon: {horizon}
Key Metrics:
- Current Price: {current_price}
- SMA 50: {sma_50}
- SMA 200: {sma_200}
- P/E Ratio: {pe_ratio}
- Revenue Growth: {revenue_growth}
- Profit Margin: {profit_margin}
- Debt/Equity: {debt_to_equity}
- Volatility (annualized): {volatility}
- Max Drawdown: {max_drawdown}
{alternatives_section}"""

BATCH_ALTERNATIVES_SECTION_TEMPLATE = """\
Alternatives Context:
- Health Score: {health_score}/100
- Profile Fit Score: {profile_fit_score}/100
- Portfolio Role: {portfolio_role}
- Trigger Reasons: {trigger_reasons}
{news_flags_context}"""

BATCH_INSIGHT_PROMPT_TEMPLATE = """\
Analyze the following asset states and provide an educational explanation for each one.

{user_context}

{asset_blocks}

For each asset that includes an "Alternatives Context" section, additionally suggest \
3-5 alternative tickers in the same portfolio role that may be more suitable, each \
with a one-line educational reason (not a recommendation). NEVER use prescriptive \
language—describe characteristics, not actions.

Respond with a single JSON object keyed by ticker, with exactly one entry per asset above:
{{
  "TICKER": {{
    "scenario": "A 1-2 sentence description of the most likely scenario without price predictions",
    "risks": ["risk1", "risk2", "risk3"],
    "explanation": "A 3-5 sentence educational explanation of what this means for the investor",
    "alternatives": [
      {{"ticker": "TICKER1", "reason": "One-line educational reason"}}
    ]
  }}
}}
Include the "alternatives" key only for assets that have an Alternatives Context section.
Respond with compact JSON on a single line — no indentation or extra whitespace."""


def build_user_context(user_profile) -> str:
    if user_profile is None:
        return ""
    return (
        f"User Profile: Risk tolerance={user_profile.risk}, "
        f"Horizon={user_profile.horizon}, Objective={user_profile.objective}"
    )
