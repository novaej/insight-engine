from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from insight_engine.rules.change_rules import ChangeEvent
from insight_engine.services import monitoring


def _provider():
    p = MagicMock()
    prices = pd.Series(100 + np.cumsum(np.random.default_rng(0).normal(0, 0.5, 250)))
    p.fetch_history.return_value = pd.DataFrame(
        {"Close": prices, "High": prices + 1, "Low": prices - 1}
    )
    p.fetch_info.return_value = {"quoteType": "EQUITY", "sector": "Technology"}
    p.fetch_news.return_value = []
    p.fetch_holdings.return_value = []
    return p


def _user(email="u@example.com", alerts=True, uid=1):
    u = MagicMock()
    u.id = uid
    u.email = email
    u.alerts_enabled = alerts
    return u


def _portfolio(uid=1, pid=1):
    p = MagicMock()
    p.id = pid
    p.user_id = uid
    p.user_profile = {"risk": "moderate", "horizon": "long", "goal": "growth"}
    return p


def _position(ticker="AAPL", pid=1):
    p = MagicMock()
    p.ticker = ticker
    p.portfolio_id = pid
    return p


def _session(user, portfolio, positions, latest_record=None):
    """Session whose execute() returns the right rows per query, in call order:
    users, then per user: portfolio, positions, then per ticker: latest insight."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    results = [
        _scalars([user]),          # users sweep
        _scalar(portfolio),        # portfolio for user
        _scalars(positions),       # positions
    ]
    for _ in positions:
        results.append(_scalar(latest_record))  # latest snapshot per ticker
    session.execute = AsyncMock(side_effect=results)
    return session


def _scalars(items):
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    return r


def _scalar(item):
    r = MagicMock()
    r.scalar_one_or_none.return_value = item
    return r


@pytest.mark.asyncio
async def test_baseline_run_sends_nothing():
    email = MagicMock()
    email.send.return_value = True
    session = _session(_user(), _portfolio(), [_position("AAPL")], latest_record=None)

    summary = await monitoring.run_monitoring(session, _provider(), email)

    assert summary["users_swept"] == 1
    assert summary["changes_detected"] == 0
    assert summary["emails_sent"] == 0
    email.send.assert_not_called()
    session.add.assert_called()  # baseline insight persisted


@pytest.mark.asyncio
async def test_change_triggers_one_email():
    email = MagicMock()
    email.send.return_value = True
    session = _session(_user(), _portfolio(), [_position("AAPL")], latest_record=None)

    with patch.object(
        monitoring, "detect_changes",
        return_value=[ChangeEvent("AAPL", "state_worsened", "AAPL: state changed.")],
    ):
        summary = await monitoring.run_monitoring(session, _provider(), email)

    assert summary["changes_detected"] == 1
    assert summary["emails_sent"] == 1
    email.send.assert_called_once()
    subject = email.send.call_args.args[1]
    assert "1 update" in subject


@pytest.mark.asyncio
async def test_skips_user_without_positions():
    email = MagicMock()
    session = _session(_user(), _portfolio(), positions=[])

    summary = await monitoring.run_monitoring(session, _provider(), email)

    assert summary["users_swept"] == 0
    email.send.assert_not_called()
