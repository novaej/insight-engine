from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import RiskLevel


def evaluate_risk(metrics: MetricsSummary) -> RiskLevel:
    """Evaluate risk based on volatility and max drawdown.

    Thresholds:
    - High: annualized volatility > 40% OR max drawdown < -30%
    - Low: annualized volatility < 20% AND max drawdown > -15%
    - Medium: everything else
    """
    vol = metrics.annualized_volatility
    dd = metrics.max_drawdown

    if vol is None and dd is None:
        return RiskLevel.medium

    high_vol = vol is not None and vol > 0.40
    severe_dd = dd is not None and dd < -0.30

    if high_vol or severe_dd:
        return RiskLevel.high

    low_vol = vol is not None and vol < 0.20
    mild_dd = dd is not None and dd > -0.15

    if low_vol and mild_dd:
        return RiskLevel.low

    return RiskLevel.medium
