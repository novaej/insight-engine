from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import MarketContext


def evaluate_market_context(metrics: MetricsSummary) -> MarketContext:
    """Evaluate broad market context based on S&P 500 position vs SMA 200.

    - Favorable: S&P 500 is above its 200-day SMA
    - Adverse: S&P 500 is below its 200-day SMA
    - Default to favorable if data unavailable (conservative assumption)
    """
    if metrics.sp500_above_sma200 is None:
        return MarketContext.favorable

    if metrics.sp500_above_sma200:
        return MarketContext.favorable
    else:
        return MarketContext.adverse
