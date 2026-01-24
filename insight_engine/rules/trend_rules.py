from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import Trend


def evaluate_trend(metrics: MetricsSummary) -> Trend:
    """Evaluate trend based on SMA alignment and Parabolic SAR confirmation.

    SMA logic determines the base trend:
    - Bullish: Price > SMA50 > SMA200
    - Bearish: Price < SMA50 < SMA200
    - Sideways: mixed or insufficient SMA data

    When Parabolic SAR is available, it confirms or moderates the SMA signal:
    - Clear SMA trend + SAR agrees → confirmed trend
    - Clear SMA trend + SAR disagrees → sideways (conflict)
    - Sideways SMA + SAR available → SAR provides direction
    """
    price = metrics.current_price
    sma50 = metrics.sma_50
    sma200 = metrics.sma_200
    sar = metrics.parabolic_sar

    if price is None or sma50 is None or sma200 is None:
        return Trend.sideways

    # Determine base SMA trend
    if price > sma50 > sma200:
        sma_trend = Trend.bullish
    elif price < sma50 < sma200:
        sma_trend = Trend.bearish
    else:
        sma_trend = Trend.sideways

    # If SAR unavailable, return SMA trend as before
    if sar is None:
        return sma_trend

    sar_bullish = price > sar

    if sma_trend == Trend.bullish:
        return Trend.bullish if sar_bullish else Trend.sideways
    elif sma_trend == Trend.bearish:
        return Trend.bearish if not sar_bullish else Trend.sideways
    else:
        # SMA is sideways — SAR provides direction
        return Trend.bullish if sar_bullish else Trend.bearish
