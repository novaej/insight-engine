from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import MarketContext


def evaluate_market_context(metrics: MetricsSummary) -> MarketContext:
    """Evaluate market context from the asset's role benchmark vs its SMA 200.

    - Favorable: the benchmark index is above its 200-day SMA
    - Adverse: the benchmark index is below its 200-day SMA
    - Default to favorable if benchmark data unavailable (documented default;
      metrics.benchmark_above_sma200 stays None so the gap is visible)
    """
    if metrics.benchmark_above_sma200 is None:
        return MarketContext.favorable

    if metrics.benchmark_above_sma200:
        return MarketContext.favorable
    else:
        return MarketContext.adverse
