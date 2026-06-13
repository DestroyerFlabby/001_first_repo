from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.model_portfolio_service import (
    MODEL_MAX_NAME_WEIGHT,
    MODEL_MAX_NAMES_PER_SECTOR,
    MODEL_MAX_POSITIONS,
    MODEL_MAX_SECTOR_WEIGHT,
    _average_drawdown_adjusted_weights,
    _average_drawdown_sell_point_pct,
    _asset_available,
    _drawdown_adjusted_weights,
    _select_candidates,
    _target_weights,
    systematic_model_portfolio_response,
)


class Bar:
    def __init__(self, day: date, close: Decimal, volume: Decimal = Decimal("1")) -> None:
        self.day = day
        self.close = close
        self.volume = volume


def asset_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": "AAA",
        "asset_type": "stock",
        "status": "active",
        "strategy_eligible": True,
        "added_at": "2026-01-31",
        "archived_at": "",
    }
    row.update(overrides)
    return row


def candidate(ticker: str, sector: str, score: int) -> dict[str, object]:
    return {
        "ticker": ticker,
        "sector": sector,
        "model_score": Decimal(score),
    }


def test_asset_availability_respects_added_and_archived_dates() -> None:
    row = asset_row(added_at="2026-02-10", archived_at="2026-03-10", status="archived")
    assert not _asset_available(row, date(2026, 2, 9))
    assert _asset_available(row, date(2026, 2, 10))
    assert _asset_available(row, date(2026, 3, 9))
    assert not _asset_available(row, date(2026, 3, 10))


def test_candidate_selection_caps_names_and_sector_count() -> None:
    rows = [candidate(f"TECH{index}", "Technology", 200 - index) for index in range(12)]
    rows += [candidate(f"SECTOR{index}", f"Sector {index}", 150 - index) for index in range(30)]
    selected = _select_candidates(rows)
    assert len(selected) == MODEL_MAX_POSITIONS
    assert sum(row["sector"] == "Technology" for row in selected) <= MODEL_MAX_NAMES_PER_SECTOR


def test_target_weights_apply_name_and_sector_caps() -> None:
    rows = [candidate(f"TECH{index}", "Technology", 200 - index) for index in range(5)]
    rows += [candidate(f"OTHER{index}", f"Sector {index}", 150 - index) for index in range(15)]
    weights = _target_weights(rows)
    assert sum(weights.values()) <= Decimal("0.95")
    assert max(weights.values()) <= MODEL_MAX_NAME_WEIGHT
    technology_weight = sum(weights[row["ticker"]] for row in rows if row["sector"] == "Technology")
    assert technology_weight <= MODEL_MAX_SECTOR_WEIGHT


def test_drawdown_overlay_exits_unsupported_hard_drawdown() -> None:
    observed = date(2026, 3, 2)
    holdings = {"AAA": {"peak_price": Decimal("100"), "entry_signal": "near"}}
    charts = {"AAA": (Bar(observed, Decimal("80")),)}
    weights = {"AAA": Decimal("0.05")}
    selected = [
        {
            "ticker": "AAA",
            "entry_signal": "near",
            "five_day_volume_ratio": 0.9,
            "one_month_relative_strength_pct": -4,
            "news_active": False,
            "news_accelerating": False,
        }
    ]

    adjusted = _drawdown_adjusted_weights(observed, selected, weights, holdings, charts)

    assert adjusted["AAA"] == Decimal("0")
    assert "hard drawdown exit" in holdings["AAA"]["drawdown_control_reason"]


def test_drawdown_overlay_keeps_supported_drawdown() -> None:
    observed = date(2026, 3, 2)
    holdings = {"AAA": {"peak_price": Decimal("100"), "entry_signal": "fresh"}}
    charts = {"AAA": (Bar(observed, Decimal("83")),)}
    weights = {"AAA": Decimal("0.05")}
    selected = [
        {
            "ticker": "AAA",
            "entry_signal": "fresh",
            "five_day_volume_ratio": 1.4,
            "one_month_relative_strength_pct": 2,
            "news_active": True,
            "news_accelerating": True,
        }
    ]

    adjusted = _drawdown_adjusted_weights(observed, selected, weights, holdings, charts)

    assert adjusted["AAA"] == Decimal("0.05")
    assert "drawdown_control_reason" not in holdings["AAA"]


def test_average_drawdown_sell_point_uses_trailing_adverse_moves() -> None:
    holding = {"daily_adverse_moves_pct": [-2, -3, -4]}

    sell_point = _average_drawdown_sell_point_pct(holding)
    intraday_proxy = _average_drawdown_sell_point_pct(holding, intraday_proxy=True)

    assert sell_point == Decimal("-7.5")
    assert intraday_proxy == Decimal("-5.625")


def test_average_drawdown_overlay_exits_at_eod_sell_point() -> None:
    observed = date(2026, 3, 2)
    holdings = {
        "AAA": {
            "peak_price": Decimal("100"),
            "entry_signal": "strict",
            "daily_adverse_moves_pct": [-2, -3, -4],
        }
    }
    charts = {"AAA": (Bar(observed, Decimal("91")),)}
    weights = {"AAA": Decimal("0.05")}
    selected = [
        {
            "ticker": "AAA",
            "entry_signal": "strict",
            "five_day_volume_ratio": 0.9,
            "one_month_relative_strength_pct": -1,
            "news_active": False,
            "news_accelerating": False,
        }
    ]

    adjusted = _average_drawdown_adjusted_weights(observed, selected, weights, holdings, charts)

    assert adjusted["AAA"] == Decimal("0")
    assert "average daily drawdown sell point" in holdings["AAA"]["drawdown_control_reason"]


def test_model_response_reports_selected_window_return_separately() -> None:
    inception = systematic_model_portfolio_response(date(2026, 6, 12), date(2026, 1, 31))
    selected = systematic_model_portfolio_response(date(2026, 6, 12), date(2026, 5, 20))

    assert inception["from_date"] == "2026-02-02"
    assert selected["from_date"] == "2026-05-20"
    assert selected["return_pct"] != selected["inception_return_pct"]
    assert selected["inception_return_pct"] == inception["inception_return_pct"]
    assert selected["selected_start_value"] != selected["initial_value"]
