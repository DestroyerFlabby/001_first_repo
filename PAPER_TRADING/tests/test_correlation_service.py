from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.correlation_service import (  # noqa: E402
    correlation_response,
    direct_overlap_response,
    pair_correlation,
    top_positions,
)


START = date(2026, 1, 1)


def returns(values: list[float], missing: set[int] | None = None) -> dict[date, float]:
    missing = missing or set()
    return {START + timedelta(days=index): value for index, value in enumerate(values) if index not in missing}


def test_perfect_positive_and_negative_correlation() -> None:
    left = returns([1, 2, 3, 4])
    positive = pair_correlation(left, returns([2, 4, 6, 8]), minimum_observations=4)
    negative = pair_correlation(left, returns([-2, -4, -6, -8]), minimum_observations=4)

    assert round(positive["correlation"], 8) == 1
    assert round(negative["correlation"], 8) == -1


def test_missing_dates_are_aligned_without_filling() -> None:
    result = pair_correlation(
        returns([1, 2, 3, 4], missing={1}),
        returns([2, 4, 6, 8], missing={2}),
        minimum_observations=2,
    )

    assert result["observations"] == 2
    assert round(result["correlation"], 8) == 1


def test_zero_variance_and_insufficient_history_are_unavailable() -> None:
    zero = pair_correlation(returns([1, 1, 1]), returns([1, 2, 3]), minimum_observations=3)
    short = pair_correlation(returns([1, 2]), returns([2, 4]), minimum_observations=3)

    assert zero["correlation"] is None
    assert zero["warning"] == "zero-variance return series"
    assert short["correlation"] is None
    assert short["warning"] == "insufficient aligned history"


def test_top_positions_are_limited_to_twelve() -> None:
    detail = {
        "positions": [
            {"ticker": f"T{index:02}", "current_value": index}
            for index in range(1, 16)
        ]
    }

    selected = top_positions(detail)

    assert len(selected) == 12
    assert selected[0]["ticker"] == "T15"
    assert selected[-1]["ticker"] == "T04"


def test_direct_overlap_uses_minimum_portfolio_weights() -> None:
    left = {"investor": "Left", "positions": [{"ticker": "AAA", "current_value": 60}, {"ticker": "BBB", "current_value": 40}]}
    right = {"investor": "Right", "positions": [{"ticker": "AAA", "current_value": 25}, {"ticker": "CCC", "current_value": 75}]}

    result = direct_overlap_response(left, right)

    assert result["shared_tickers"] == ["AAA"]
    assert result["direct_overlap_pct"] == 25
    assert result["etf_lookthrough"]["available"] is False


def test_response_preserves_missing_history_warnings() -> None:
    detail = {
        "investor": "Test",
        "positions": [
            {"ticker": "AAA", "security_type": "stock", "current_value": 60},
            {"ticker": "BBB", "security_type": "stock", "current_value": 40},
        ],
    }

    def loader(ticker: str, asset_type: str, start: date, end: date) -> dict[date, float]:
        del asset_type, start, end
        if ticker == "AAA":
            return {START + timedelta(days=index): 100 + index for index in range(6)}
        return {START: 100}

    result = correlation_response(detail, START, START + timedelta(days=10), price_loader=loader, minimum_observations=3)

    assert result["average_correlation"] is None
    assert result["data_quality"]["unavailable_pair_count"] == 1
    assert any("BBB" in warning for warning in result["data_quality"]["warnings"])
    assert result["diversification_warning"]
