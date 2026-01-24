from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import Trend


def evaluate_trend(metrics: MetricsSummary) -> Trend:
    """Evaluate trend based on price alignment with SMA 50 and SMA 200.

    - Bullish: Price > SMA50 > SMA200
    - Bearish: Price < SMA50 < SMA200
    - Sideways: everything else or insufficient data
    """
    price = metrics.current_price
    sma50 = metrics.sma_50
    sma200 = metrics.sma_200

    if price is None or sma50 is None or sma200 is None:
        return Trend.sideways

    if price > sma50 > sma200:
        return Trend.bullish
    elif price < sma50 < sma200:
        return Trend.bearish
    else:
        return Trend.sideways
