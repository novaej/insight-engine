import logging

from insight_engine.ai.handlers import generate_explanation
from insight_engine.services.analysis import analyze_asset

logger = logging.getLogger(__name__)


def run_daily_analysis(tickers: list[str]) -> list[dict]:
    """Run daily analysis for all portfolio tickers.

    This can be triggered via a cron job or an API endpoint.
    Returns a list of insight summaries.
    """
    results = []
    for ticker in tickers:
        try:
            insight, _info = analyze_asset(ticker)
            insight = generate_explanation(insight)
            results.append({
                "ticker": insight.ticker,
                "asset_state": insight.asset_state.value,
                "horizon": insight.horizon.value,
                "scenario": insight.scenario,
                "risks": insight.risks,
            })
            logger.info(f"Analyzed {ticker}: {insight.asset_state.value}")
        except Exception as e:
            logger.error(f"Failed to analyze {ticker}: {e}")
            results.append({"ticker": ticker, "error": str(e)})

    return results
