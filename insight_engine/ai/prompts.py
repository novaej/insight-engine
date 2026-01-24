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


def build_user_context(user_profile) -> str:
    if user_profile is None:
        return ""
    return (
        f"User Profile: Risk tolerance={user_profile.risk}, "
        f"Horizon={user_profile.horizon}, Objective={user_profile.objective}"
    )
