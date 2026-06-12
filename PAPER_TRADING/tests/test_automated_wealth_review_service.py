from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.automated_wealth_review_service import automated_wealth_review_response  # noqa: E402


def allocation(complete: float = 95, asset_type: float = 98, top_position: float = 5, top_five: float = 30) -> dict[str, object]:
    return {
        "metadata_coverage": {
            "complete_value_pct": complete,
            "asset_type_value_pct": asset_type,
        },
        "concentration": {
            "top_position_weight_pct": top_position,
            "top_five_weight_pct": top_five,
        },
        "concentration_alerts": [],
    }


def weights(core: float = 55, growth: float = 30, defensive: float = 15) -> list[dict[str, object]]:
    return [
        {"basket_id": "ai-wealth-core", "current_weight": core},
        {"basket_id": "ai-wealth-growth", "current_weight": growth},
        {"basket_id": "ai-wealth-defensive-income", "current_weight": defensive},
    ]


def review(**kwargs: object) -> dict[str, object]:
    return automated_wealth_review_response(
        date(2026, 1, 31),
        date(2026, 6, 5),
        kwargs.pop("allocation_payload", allocation()),
        current_weights=kwargs.pop("current_weights", weights()),
        portfolio_value=Decimal("100000"),
        **kwargs,
    )


def test_clean_allocation_produces_no_action_required() -> None:
    payload = review()

    assert payload["review_status"] == "no_action_required"
    assert payload["rebalance_health"]["draft_available"] is True


def test_out_of_band_allocation_produces_rebalance_review_required() -> None:
    payload = review(current_weights=weights(30, 55, 15))

    assert payload["review_status"] == "rebalance_review_required"
    assert payload["rebalance_health"]["draft_available"] is True


def test_low_metadata_coverage_produces_data_quality_review_required() -> None:
    payload = review(allocation_payload=allocation(complete=60, asset_type=88))

    assert payload["review_status"] == "data_quality_review_required"
    assert payload["rebalance_health"]["draft_available"] is False


def test_risk_breach_produces_risk_review_required() -> None:
    payload = review(risk_payload={"metrics": {"current_drawdown_pct": -9, "max_drawdown_pct": -10}, "alerts": []})

    assert payload["review_status"] == "risk_review_required"
    assert any("drawdown" in warning.casefold() for warning in payload["warnings"])


def test_missing_weights_produces_policy_profile_required() -> None:
    payload = review(current_weights=[])

    assert payload["review_status"] == "policy_profile_required"
    assert payload["rebalance_health"]["draft_available"] is False


def test_draft_rebalance_is_not_produced_when_blockers_exist_and_is_read_only() -> None:
    payload = review(allocation_payload=allocation(complete=50), current_weights=weights(30, 55, 15))

    assert payload["rebalance_health"]["draft_available"] is False
    assert payload["data_quality"]["write_behavior"] == "read_only_no_orders"
