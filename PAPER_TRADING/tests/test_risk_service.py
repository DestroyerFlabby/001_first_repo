from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.risk_service import portfolio_risk_response


def series(values: list[float]) -> list[dict[str, object]]:
    start = date(2026, 1, 1)
    return [{"date": (start + timedelta(days=index)).isoformat(), "value": value} for index, value in enumerate(values)]


def test_risk_metrics_capture_drawdown_and_concentration() -> None:
    detail = {
        "investor": "test",
        "series": series([100, 110, 90, 95, 115]),
        "positions": [
            {"ticker": "AAA", "sector": "Technology", "current_value": 70},
            {"ticker": "BBB", "sector": "Financials", "current_value": 30},
        ],
        "benchmark_comparison": {"benchmark_series": series([100, 102, 101, 103, 105])},
    }
    response = portfolio_risk_response(detail, date(2026, 1, 1), date(2026, 1, 5))
    metrics = response["metrics"]
    assert metrics["maximum_drawdown_pct"] < -18
    assert metrics["current_drawdown_pct"] == 0
    assert metrics["largest_position_weight_pct"] == 70
    assert metrics["effective_number_of_holdings"] < 2
    assert any(alert["type"] == "position_concentration" for alert in response["alerts"])


def test_missing_history_is_explicitly_low_confidence() -> None:
    response = portfolio_risk_response(
        {"investor": "empty", "series": [], "positions": [], "benchmark_comparison": {}},
        date(2026, 1, 1),
        date(2026, 1, 31),
    )
    assert response["data_quality"]["confidence"] == "low"
    assert response["metrics"]["beta"] is None
    assert len(response["data_quality"]["warnings"]) >= 3


def test_sector_alert_uses_current_position_values() -> None:
    detail = {
        "investor": "sector-heavy",
        "series": series([100 + index for index in range(30)]),
        "positions": [
            {"ticker": "AAA", "sector": "Technology", "current_value": 40},
            {"ticker": "BBB", "sector": "Technology", "current_value": 30},
            {"ticker": "CCC", "sector": "Other", "current_value": 30},
        ],
        "benchmark_comparison": {"benchmark_series": series([100 + index * 0.5 for index in range(30)])},
    }
    response = portfolio_risk_response(detail, date(2026, 1, 1), date(2026, 1, 30))
    assert response["sector_concentration"][0]["weight_pct"] == 70
    assert any(alert["type"] == "sector_concentration" for alert in response["alerts"])
