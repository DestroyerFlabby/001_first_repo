from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.scenario_service import scenario_response  # noqa: E402


def scenario(payload: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(row for row in scenario_response(payload)["scenarios"] if row["scenario_id"] == scenario_id)


def test_scenario_impacts_have_expected_signs_and_reconcile() -> None:
    payload = {
        "investor": "Test",
        "as_of": "2026-06-11",
        "positions": [
            {"ticker": "TECH", "current_value": 50, "asset_type": "stock", "sector": "AI Technology", "currency": "USD"},
            {"ticker": "BANK", "current_value": 30, "asset_type": "stock", "sector": "Financials", "currency": "CAD"},
            {"ticker": "BTC", "current_value": 20, "asset_type": "crypto", "sector": "Crypto", "currency": "USD"},
        ],
    }
    response = scenario_response(payload)

    expected = {
        "broad-equity-down-20": -16.0,
        "technology-ai-down-30": -18.0,
        "crypto-down-40": -8.0,
        "cad-strengthens-10": -7.0,
        "largest-position-down-35": -17.5,
    }
    for row in response["scenarios"]:
        assert round(row["estimated_impact_pct"], 8) == expected[row["scenario_id"]]
        assert abs(row["reconciliation_difference_pct"]) < 0.000001
        assert row["estimated_dollar_impact"] <= 0


def test_largest_position_contribution_is_deterministic() -> None:
    payload = {
        "positions": [
            {"ticker": "SMALL", "current_value": 40, "asset_type": "stock", "sector": "Industrials", "currency": "USD"},
            {"ticker": "LARGE", "current_value": 60, "asset_type": "stock", "sector": "Industrials", "currency": "USD"},
        ]
    }

    result = scenario(payload, "largest-position-down-35")

    assert result["affected_position_count"] == 1
    assert result["largest_affected_positions"][0]["ticker"] == "LARGE"
    assert result["estimated_dollar_impact"] == -21


def test_missing_metadata_stays_unassigned_and_warned() -> None:
    payload = {"positions": [{"ticker": "UNKNOWN", "current_value": 100}]}
    response = scenario_response(payload)

    assert all(row["affected_position_count"] == 0 for row in response["scenarios"][:-1])
    assert any("missing asset type, sector, currency" in warning for warning in response["data_quality"]["warnings"])
    assert scenario(payload, "largest-position-down-35")["estimated_impact_pct"] == -35


def test_zero_value_portfolio_has_stable_read_only_contract() -> None:
    response = scenario_response({"positions": [{"ticker": "ZERO", "current_value": 0}]})

    assert response["total_current_value"] == 0
    assert response["position_count"] == 0
    assert all(row["estimated_impact_pct"] == 0 for row in response["scenarios"])
    assert response["data_quality"]["write_behavior"] == "read_only_no_orders"
    assert any("No positive current position values" in warning for warning in response["data_quality"]["warnings"])


def test_supplied_weights_are_normalized_from_values_with_warning() -> None:
    payload = {
        "positions": [
            {"ticker": "A", "current_value": 75, "weight_pct": 40, "asset_type": "stock", "sector": "Industrials", "currency": "USD"},
            {"ticker": "B", "current_value": 25, "weight_pct": 20, "asset_type": "stock", "sector": "Industrials", "currency": "USD"},
        ]
    }
    response = scenario_response(payload)

    broad = next(row for row in response["scenarios"] if row["scenario_id"] == "broad-equity-down-20")
    assert broad["estimated_impact_pct"] == -20
    assert any("weights total 60.00%" in warning for warning in response["data_quality"]["warnings"])
