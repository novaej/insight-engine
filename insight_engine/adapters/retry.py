import functools
import logging
import time

logger = logging.getLogger(__name__)


def with_retry(attempts: int = 3, base_delay: float = 0.5):
    """Retry a function on any exception with exponential backoff.

    Tolerates transient market-data failures (rate limits, flaky network) that
    are common when a portfolio analysis fires many fetches concurrently.
    Re-raises the last exception if every attempt fails.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:  # noqa: BLE001 - transient, retried/re-raised
                    last_error = e
                    if attempt < attempts - 1:
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            "%s failed (attempt %d/%d), retrying in %.1fs: %s",
                            func.__name__, attempt + 1, attempts, delay, e,
                        )
                        time.sleep(delay)
            raise last_error

        return wrapper

    return decorator
