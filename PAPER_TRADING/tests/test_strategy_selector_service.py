from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.strategy_selector_service import strategy_selector_response  # noqa: E402


def detail(
    name: str,
    *,
    return_pct: float,
    alpha_pct: float,
    drawdown_pct: float,
    volatility_pct: float = 12,
    top_five_pct: float = 35,
    sector_pct: float = 25,
    turnover_pct: float = 40,
    trades: int = 20,
    points: int = 40,
) -> dict[str, object]:
    start = date(2026, 1, 31)
    series = [{"date": (start + timedelta(days=index)).isoformat(), "value": 100000 + index} for index in range(points)]
    return {
        "portfolio_name": name,
        "return_pct": return_pct,
        "positions": [
            {"ticker": f"{name[:3]}{index}", "portfolio_weight_pct": top_five_pct / 5, "sector": "Technology"}
            for index in range(5)
        ],
        "realized_positions": [{"return_pct": 5}, {"return_pct": 8}, {"return_pct": -2}],
        "trade_ledger": [{} for _ in range(trades)],
        "series": series,
        "benchmark_comparison": {
            "alpha_pct": alpha_pct,
            "max_drawdown_pct": drawdown_pct,
            "volatility_pct": volatility_pct,
        },
        "statistics": {
            "top_five_weight_pct": top_five_pct,
            "largest_sector_weight_pct": sector_pct,
            "total_turnover_pct": turnover_pct,
            "total_trades": trades,
        },
        "methodology": {"execution_convention": "execute at the next available close"},
    }


def response(*details: dict[str, object]) -> dict[str, object]:
    return strategy_selector_response(date(2026, 1, 31), date(2026, 6, 5), list(details))


def test_model_wins_when_risk_adjusted_score_is_stronger() -> None:
    payload = response(
        detail("systematic-model-portfolio", return_pct=25, alpha_pct=10, drawdown_pct=-6),
        detail("daily-eod-rotation-portfolio", return_pct=18, alpha_pct=6, drawdown_pct=-12),
    )

    assert payload["recommendation_status"] == "hold_model"
    assert payload["ranked_strategies"][0]["strategy_id"] == "systematic-model-portfolio"


def test_high_return_high_drawdown_strategy_is_penalized() -> None:
    payload = response(
        detail("systematic-model-portfolio", return_pct=20, alpha_pct=8, drawdown_pct=-6),
        detail("daily-eod-rotation-portfolio", return_pct=45, alpha_pct=20, drawdown_pct=-35, volatility_pct=45),
    )

    assert payload["ranked_strategies"][0]["strategy_id"] == "systematic-model-portfolio"
    assert any("drawdown" in warning.casefold() for warning in payload["ranked_strategies"][1]["warnings"])


def test_concentrated_strategy_is_penalized() -> None:
    payload = response(
        detail("systematic-model-portfolio", return_pct=15, alpha_pct=5, drawdown_pct=-5, top_five_pct=35),
        detail("concentrated-winner", return_pct=22, alpha_pct=7, drawdown_pct=-6, top_five_pct=85, sector_pct=75),
    )

    concentrated = next(row for row in payload["ranked_strategies"] if row["strategy_id"] == "concentrated-winner")
    assert concentrated["score_components"]["concentration_score"] < 50
    assert any("concentration" in warning.casefold() for warning in concentrated["warnings"])


def test_insufficient_data_triggers_manual_review() -> None:
    payload = response(detail("thin-history", return_pct=30, alpha_pct=12, drawdown_pct=-4, trades=1, points=5))

    assert payload["recommendation_status"] == "manual_review_required"
    assert payload["data_quality"]["manual_review_required"] is True


def test_blend_respects_tactical_caps_and_is_read_only() -> None:
    payload = response(
        detail("systematic-model-portfolio", return_pct=25, alpha_pct=10, drawdown_pct=-6),
        detail("daily-eod-rotation-portfolio", return_pct=18, alpha_pct=6, drawdown_pct=-12),
    )

    tactical = sum(row["target_weight_pct"] for row in payload["draft_blend"] if row["sleeve"] != "core_policy")
    assert tactical <= 40
    assert payload["data_quality"]["write_behavior"] == "read_only_no_orders"
