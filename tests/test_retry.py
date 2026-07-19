from unittest.mock import patch

import pytest

from insight_engine.adapters.retry import with_retry


def test_succeeds_first_try():
    calls = []

    @with_retry(attempts=3, base_delay=0)
    def ok():
        calls.append(1)
        return "value"

    assert ok() == "value"
    assert len(calls) == 1


def test_retries_then_succeeds():
    calls = []

    @with_retry(attempts=3, base_delay=0)
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("transient")
        return "recovered"

    with patch("insight_engine.adapters.retry.time.sleep"):
        assert flaky() == "recovered"
    assert len(calls) == 3


def test_reraises_after_exhausting_attempts():
    calls = []

    @with_retry(attempts=2, base_delay=0)
    def always_fails():
        calls.append(1)
        raise ValueError("nope")

    with patch("insight_engine.adapters.retry.time.sleep"):
        with pytest.raises(ValueError, match="nope"):
            always_fails()
    assert len(calls) == 2
