from insight_engine.domain.enums import AssetState
from insight_engine.rules.change_rules import (
    ADVERSE,
    FAVORABLE,
    Snapshot,
    detect_changes,
)


def _snap(**kw):
    base = dict(
        ticker="AAPL",
        asset_state=AssetState.healthy,
        health_score=70,
        current_price=100.0,
        sma_200=90.0,
        parabolic_sar=88.0,
        max_drawdown=-0.10,
        news_flags={"regulatory_risk": False, "earnings_negative": False,
                    "management_change": False, "litigation_risk": False},
    )
    base.update(kw)
    return Snapshot(**base)


def test_no_previous_is_baseline():
    assert detect_changes(None, _snap(), "moderate") == []


def test_unchanged_yields_nothing():
    assert detect_changes(_snap(), _snap(), "moderate") == []


def test_state_worsened():
    events = detect_changes(_snap(), _snap(asset_state=AssetState.risky), "moderate")
    kinds = {e.kind for e in events}
    assert "state_worsened" in kinds


def test_state_improved_is_favorable():
    events = detect_changes(
        _snap(asset_state=AssetState.risky), _snap(asset_state=AssetState.healthy), "moderate"
    )
    improved = [e for e in events if e.kind == "state_improved"]
    assert len(improved) == 1
    assert improved[0].direction == FAVORABLE
    assert all(e.kind != "state_worsened" for e in events)


def test_health_rise_is_favorable():
    events = detect_changes(_snap(health_score=50), _snap(health_score=70), "moderate")
    rises = [e for e in events if e.kind == "health_rise"]
    assert len(rises) == 1
    assert rises[0].direction == FAVORABLE


def test_price_cross_above_is_favorable():
    prev = _snap(current_price=85.0, sma_200=90.0)   # below
    curr = _snap(current_price=95.0, sma_200=90.0)   # above
    events = detect_changes(prev, curr, "moderate")
    assert any(e.kind == "sma200_cross_above" and e.direction == FAVORABLE for e in events)


def test_sar_turned_bullish_is_favorable():
    prev = _snap(current_price=90.0, parabolic_sar=95.0)  # price below SAR
    curr = _snap(current_price=100.0, parabolic_sar=95.0)  # price above SAR
    events = detect_changes(prev, curr, "moderate")
    assert any(e.kind == "sar_bullish" and e.direction == FAVORABLE for e in events)


def test_adverse_events_tagged_adverse():
    prev = _snap(asset_state=AssetState.healthy, health_score=80)
    curr = _snap(asset_state=AssetState.risky, health_score=55)
    events = detect_changes(prev, curr, "moderate")
    assert events and all(e.direction == ADVERSE for e in events)


def test_health_drop():
    events = detect_changes(_snap(health_score=70), _snap(health_score=50), "moderate")
    assert any(e.kind == "health_drop" for e in events)
    # A small drop under the threshold does not fire
    small = detect_changes(_snap(health_score=70), _snap(health_score=60), "moderate")
    assert all(e.kind != "health_drop" for e in small)


def test_sma200_cross_below():
    prev = _snap(current_price=100.0, sma_200=90.0)   # above
    curr = _snap(current_price=85.0, sma_200=90.0)    # below
    events = detect_changes(prev, curr, "moderate")
    assert any(e.kind == "sma200_cross_below" for e in events)


def test_sar_turned_bearish():
    prev = _snap(current_price=100.0, parabolic_sar=95.0)  # price above SAR
    curr = _snap(current_price=90.0, parabolic_sar=95.0)   # price below SAR
    events = detect_changes(prev, curr, "moderate")
    assert any(e.kind == "sar_bearish" for e in events)


def test_drawdown_breach():
    prev = _snap(max_drawdown=-0.20)   # within moderate (-0.25) tolerance
    curr = _snap(max_drawdown=-0.30)   # breaches
    events = detect_changes(prev, curr, "moderate")
    assert any(e.kind == "drawdown_breach" for e in events)


def test_new_news_flag():
    prev = _snap()
    curr = _snap(news_flags={"regulatory_risk": True, "earnings_negative": False,
                             "management_change": False, "litigation_risk": False})
    events = detect_changes(prev, curr, "moderate")
    assert any(e.kind == "news_regulatory_risk" for e in events)
    # A flag already active last run is not re-reported
    both = detect_changes(curr, curr, "moderate")
    assert all(not e.kind.startswith("news_") for e in both)


def test_multiple_changes():
    prev = _snap(asset_state=AssetState.healthy, health_score=80)
    curr = _snap(asset_state=AssetState.risky, health_score=50, current_price=80.0)
    events = detect_changes(prev, curr, "moderate")
    kinds = {e.kind for e in events}
    assert {"state_worsened", "health_drop"}.issubset(kinds)
    assert len(events) >= 2
