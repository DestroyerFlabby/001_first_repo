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
    _asset_available,
    _select_candidates,
    _target_weights,
)


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
