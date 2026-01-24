from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import Valuation


def evaluate_valuation(metrics: MetricsSummary) -> Valuation:
    """Evaluate valuation by comparing current P/E to historical average.

    - Cheap: P/E < 0.8x historical average
    - Expensive: P/E > 1.2x historical average
    - Reasonable: between 0.8x and 1.2x
    - Inconclusive: insufficient data
    """
    pe = metrics.pe_ratio
    pe_avg = metrics.pe_historical_avg

    if pe is None or pe_avg is None or pe_avg <= 0:
        return Valuation.inconclusive

    ratio = pe / pe_avg

    if ratio < 0.8:
        return Valuation.cheap
    elif ratio > 1.2:
        return Valuation.expensive
    else:
        return Valuation.reasonable
