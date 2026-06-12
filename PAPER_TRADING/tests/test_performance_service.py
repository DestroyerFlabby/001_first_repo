from __future__ import annotations

import sys
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.performance_service import portfolio_performance_response


def test_performance_reconciles_realized_and_unrealized_gain() -> None:
    detail = {
        "investor": "test",
        "initial_value": 1000,
        "current_value": 1150,
        "gain_loss": 150,
        "return_pct": 15,
        "positions": [{"ticker": "AAA", "gain_loss": 100, "return_pct": 10, "current_value": 600}],
        "realized_positions": [{"ticker": "BBB", "gain_loss": 50, "return_pct": 5}],
        "series": [{"date": "2026-01-01", "value": 1000}, {"date": "2026-01-02", "value": 1150}],
        "benchmark_comparison": {"benchmark": "SPY", "benchmark_return_pct": 5, "alpha_pct": 10},
    }
    response = portfolio_performance_response(detail, date(2026, 1, 1), date(2026, 1, 2))
    assert response["summary"]["realized_gain_loss"] == 50
    assert response["summary"]["unrealized_gain_loss"] == 100
    assert response["summary"]["reconciliation_residual"] == 0
    assert response["contributions"][0]["contribution_pct"] == 10


def test_performance_flags_missing_series_and_residual() -> None:
    response = portfolio_performance_response(
        {"investor": "incomplete", "initial_value": 1000, "current_value": 1200, "gain_loss": 200, "positions": []},
        date(2026, 1, 1),
        date(2026, 2, 1),
    )
    assert response["data_quality"]["confidence"] == "low"
    assert response["summary"]["reconciliation_residual"] == 200
    assert len(response["data_quality"]["warnings"]) == 2
