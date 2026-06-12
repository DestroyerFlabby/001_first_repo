from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.rebalance_service import rebalance_preview


def balanced_current(core: float = 55, growth: float = 30, defensive: float = 15) -> list[dict[str, object]]:
    return [
        {"basket_id": "ai-wealth-core", "current_weight": core},
        {"basket_id": "ai-wealth-growth", "current_weight": growth},
        {"basket_id": "ai-wealth-defensive-income", "current_weight": defensive},
    ]


def test_within_band_produces_no_trades() -> None:
    response = rebalance_preview("balanced-growth", balanced_current(), Decimal("100000"))
    assert all(row["action"] == "hold" for row in response["allocations"])
    assert response["net_dollar_change"] == 0


def test_boundary_rebalance_is_self_financing() -> None:
    response = rebalance_preview("balanced-growth", balanced_current(30, 55, 15), Decimal("100000"))
    assert any(row["action"] == "buy" for row in response["allocations"])
    assert any(row["action"] == "sell" for row in response["allocations"])
    assert abs(response["net_dollar_change"]) < 0.01
    assert abs(sum(row["proposed_weight_pct"] for row in response["allocations"]) - 100) < 0.0001


def test_exact_target_moves_all_sleeves_to_target() -> None:
    response = rebalance_preview("balanced-growth", balanced_current(30, 55, 15), Decimal("100000"), exact_target=True)
    assert all(row["proposed_weight_pct"] == row["target_weight_pct"] for row in response["allocations"])


@pytest.mark.parametrize(
    "profile,current,error",
    [
        ("missing", balanced_current(), "unknown profile"),
        ("balanced-growth", balanced_current(50, 30, 15), "sum to 100"),
        ("balanced-growth", balanced_current(-5, 90, 15), "negative"),
        ("balanced-growth", balanced_current() + [{"basket_id": "ai-wealth-core", "current_weight": 0}], "duplicate"),
        ("balanced-growth", [{"basket_id": "unknown", "current_weight": 100}], "not allowed"),
    ],
)
def test_invalid_inputs_are_rejected(profile: str, current: list[dict[str, object]], error: str) -> None:
    with pytest.raises(ValueError, match=error):
        rebalance_preview(profile, current, Decimal("100000"))
