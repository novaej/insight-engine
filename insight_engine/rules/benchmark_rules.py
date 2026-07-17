import json
from pathlib import Path

from insight_engine.domain.enums import PortfolioRole

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "benchmarks.json"
_benchmarks: dict[str, str] | None = None


def load_benchmarks() -> dict[str, str]:
    """Load the role → benchmark ticker map from the JSON config file."""
    global _benchmarks
    if _benchmarks is None:
        with open(_CONFIG_PATH) as f:
            _benchmarks = json.load(f)
    return _benchmarks


def get_benchmark_ticker(role: PortfolioRole | None) -> str:
    """Benchmark index ticker an asset should be judged against."""
    benchmarks = load_benchmarks()
    default = benchmarks.get("default", "^GSPC")
    if role is None:
        return default
    return benchmarks.get(role.value, default)
