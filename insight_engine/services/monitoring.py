"""Monitoring watchdog: re-analyze holdings, detect changes, email a digest.

Deterministic and cheap — no AI, no alternatives. Compares each ticker's fresh
analysis to its most recent stored insight and emails the user a plain-language
summary of adverse transitions.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from insight_engine.adapters.caching import CachingMarketDataProvider
from insight_engine.domain.entities import AssetScores, UserProfile
from insight_engine.domain.enums import AssetState
from insight_engine.domain.models import InsightRecord, Portfolio, Position, User
from insight_engine.ports import EmailProvider, MarketDataProvider
from insight_engine.rules.change_rules import (
    FAVORABLE,
    ChangeEvent,
    Snapshot,
    detect_changes,
)
from insight_engine.rules.news_rules import extract_news_flags
from insight_engine.rules.scoring_rules import compute_health_score, compute_profile_fit_score
from insight_engine.services.analysis import analyze_asset
from insight_engine.services.insight_store import save_insights

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "This is an educational status update, not financial advice or a "
    "recommendation to buy, sell, or hold. It describes what changed so you can "
    "decide whether to look closer."
)


async def run_monitoring(
    session: AsyncSession,
    market_data_provider: MarketDataProvider,
    email_provider: EmailProvider,
) -> dict:
    """Sweep all alert-enabled users, detect changes, email digests.

    Returns a summary dict {users_swept, emails_sent, changes_detected}.
    """
    users = (
        await session.execute(
            select(User).where(User.alerts_enabled.is_(True), User.email != "")
        )
    ).scalars().all()

    users_swept = 0
    emails_sent = 0
    changes_detected = 0

    for user in users:
        portfolio = (
            await session.execute(
                select(Portfolio).where(Portfolio.user_id == user.id)
            )
        ).scalar_one_or_none()
        if portfolio is None:
            continue

        positions = (
            await session.execute(
                select(Position).where(Position.portfolio_id == portfolio.id)
            )
        ).scalars().all()
        if not positions:
            continue

        users_swept += 1
        profile = _profile_from(portfolio)
        events = await _sweep_portfolio(
            session, portfolio, positions, profile, market_data_provider
        )
        await session.commit()

        if events:
            changes_detected += len(events)
            subject = f"Vestio: {len(events)} update(s) in your portfolio"
            if email_provider.send(
                user.email, subject, _text_body(events), _html_body(events)
            ):
                emails_sent += 1

    return {
        "users_swept": users_swept,
        "emails_sent": emails_sent,
        "changes_detected": changes_detected,
    }


async def _sweep_portfolio(
    session, portfolio, positions, profile, provider
) -> list[ChangeEvent]:
    provider = CachingMarketDataProvider(provider)
    # Aggregate lots to distinct tickers.
    tickers = sorted({p.ticker.upper() for p in positions})

    all_events: list[ChangeEvent] = []
    for ticker in tickers:
        previous = await _latest_snapshot(session, portfolio.id, ticker)
        try:
            current, insight = _analyze_snapshot(ticker, profile, provider)
        except Exception as e:
            logger.warning("Monitoring: analysis failed for %s: %s", ticker, e)
            continue

        all_events.extend(detect_changes(previous, current, profile.risk.value))
        save_insights(session, portfolio.id, [insight])

    return all_events


def _analyze_snapshot(ticker, profile, provider):
    insight, _info = analyze_asset(ticker, profile, provider)
    health = compute_health_score(insight.dimensions, insight.metrics)
    fit = compute_profile_fit_score(insight.metrics, insight.dimensions, profile)
    insight.scores = AssetScores(health_score=health, profile_fit_score=fit)
    try:
        insight.news_flags = extract_news_flags(provider.fetch_news(ticker))
    except Exception:
        insight.news_flags = None

    snapshot = Snapshot(
        ticker=ticker,
        asset_state=insight.asset_state,
        health_score=health,
        current_price=insight.metrics.current_price,
        sma_200=insight.metrics.sma_200,
        parabolic_sar=insight.metrics.parabolic_sar,
        max_drawdown=insight.metrics.max_drawdown,
        news_flags=_news_dict(insight.news_flags),
    )
    return snapshot, insight


async def _latest_snapshot(session, portfolio_id, ticker) -> Snapshot | None:
    record = (
        await session.execute(
            select(InsightRecord)
            .where(
                InsightRecord.portfolio_id == portfolio_id,
                InsightRecord.ticker == ticker,
            )
            .order_by(InsightRecord.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if record is None:
        return None

    metrics = record.metrics or {}
    return Snapshot(
        ticker=record.ticker,
        asset_state=AssetState(record.asset_state),
        health_score=record.health_score,
        current_price=metrics.get("current_price"),
        sma_200=metrics.get("sma_200"),
        parabolic_sar=metrics.get("parabolic_sar"),
        max_drawdown=metrics.get("max_drawdown"),
        news_flags=record.news_flags,
    )


def _profile_from(portfolio: Portfolio) -> UserProfile:
    from insight_engine.api.schemas import UserProfileRequest

    data = UserProfileRequest(**portfolio.user_profile)
    return UserProfile(risk=data.risk, horizon=data.horizon, objective=data.goal)


def _news_dict(news_flags) -> dict | None:
    if news_flags is None:
        return None
    return {
        "regulatory_risk": news_flags.regulatory_risk,
        "earnings_negative": news_flags.earnings_negative,
        "management_change": news_flags.management_change,
        "litigation_risk": news_flags.litigation_risk,
    }


def _split(events: list[ChangeEvent]) -> tuple[list[ChangeEvent], list[ChangeEvent]]:
    favorable = [e for e in events if e.direction == FAVORABLE]
    adverse = [e for e in events if e.direction != FAVORABLE]
    return favorable, adverse


def _text_body(events: list[ChangeEvent]) -> str:
    favorable, adverse = _split(events)
    lines = ["Changes detected in your portfolio since the last check:", ""]
    if favorable:
        lines.append("Positive moves:")
        lines += [f"- {e.message}" for e in favorable]
        lines.append("")
    if adverse:
        lines.append("Potential concerns:")
        lines += [f"- {e.message}" for e in adverse]
        lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def _html_body(events: list[ChangeEvent]) -> str:
    favorable, adverse = _split(events)
    sections = ""
    if favorable:
        items = "".join(f"<li>{e.message}</li>" for e in favorable)
        sections += f"<p><strong>Positive moves</strong></p><ul>{items}</ul>"
    if adverse:
        items = "".join(f"<li>{e.message}</li>" for e in adverse)
        sections += f"<p><strong>Potential concerns</strong></p><ul>{items}</ul>"
    return (
        "<p>Changes detected in your portfolio since the last check:</p>"
        f"{sections}"
        f"<p style='color:#666;font-size:12px'>{DISCLAIMER}</p>"
    )
