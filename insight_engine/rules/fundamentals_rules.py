from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import Fundamentals


def evaluate_fundamentals(metrics: MetricsSummary) -> Fundamentals:
    """Evaluate fundamentals based on growth, margins, and debt.

    Scoring:
    - Revenue growth > 10%: +1
    - Profit margin > 15%: +1
    - Debt-to-equity < 1.0: +1

    Result:
    - Score 3: strong
    - Score 1-2: mixed
    - Score 0: weak
    - All None: mixed (insufficient data defaults to neutral)
    """
    score = 0
    data_points = 0

    if metrics.revenue_growth is not None:
        data_points += 1
        if metrics.revenue_growth > 0.10:
            score += 1

    if metrics.profit_margin is not None:
        data_points += 1
        if metrics.profit_margin > 0.15:
            score += 1

    if metrics.debt_to_equity is not None:
        data_points += 1
        if metrics.debt_to_equity < 1.0:
            score += 1

    if data_points == 0:
        return Fundamentals.mixed

    if score >= 3:
        return Fundamentals.strong
    elif score == 0:
        return Fundamentals.weak
    else:
        return Fundamentals.mixed
