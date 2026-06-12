from __future__ import annotations

import sys
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.allocation_service import (  # noqa: E402
    UNKNOWN,
    build_allocation_response,
    resolved_instrument_metadata,
)


METADATA = [
    {"ticker": "AAA", "asset_type": "stock", "sector": "Technology", "currency": "USD"},
    {"ticker": "BBB", "asset_type": "etf", "sector": "Broad Market", "currency": "CAD"},
]


def portfolio(name: str, positions: list[dict[str, object]]) -> dict[str, object]:
    return {"investor": name, "positions": positions}


def test_weights_overlap_and_effective_holdings() -> None:
    response = build_allocation_response(
        [
            portfolio(
                "Core",
                [
                    {"ticker": "AAA", "security_type": "stock", "current_value": 50},
                    {"ticker": "BBB", "security_type": "etf", "current_value": 50},
                ],
            ),
            portfolio("Tactical", [{"ticker": "AAA", "security_type": "stock", "current_value": 100}]),
        ],
        METADATA,
        as_of=date(2026, 6, 12),
    )

    security = response["allocation"]["security"]
    assert round(sum(row["weight_pct"] for row in security), 8) == 100
    assert security[0]["ticker"] == "AAA"
    assert security[0]["current_value"] == 150
    assert round(response["concentration"]["effective_number_of_holdings"], 2) == 1.6


def test_duplicate_portfolio_and_unknown_metadata_are_explicit() -> None:
    duplicate = portfolio("Core", [{"ticker": "AAA", "security_type": "stock", "current_value": 100}])
    response = build_allocation_response(
        [
            duplicate,
            duplicate,
            portfolio("Unknown Sleeve", [{"ticker": "ZZZ", "current_value": 100}]),
        ],
        METADATA,
        as_of=date(2026, 6, 12),
    )

    assert response["included_portfolio_count"] == 2
    assert response["metadata_coverage"]["unknown_sector_value"] == 100
    assert any(row["name"] == UNKNOWN for row in response["allocation"]["currency"])
    assert any("duplicate portfolio" in warning.lower() for warning in response["data_quality"]["warnings"])
    assert any(alert["code"] == "metadata_coverage" for alert in response["concentration_alerts"])


def test_concentration_alerts_are_decision_oriented() -> None:
    response = build_allocation_response(
        [portfolio("Focused", [{"ticker": "AAA", "security_type": "stock", "current_value": 100}])],
        METADATA,
        as_of=date(2026, 6, 12),
    )

    codes = {alert["code"] for alert in response["concentration_alerts"]}
    assert {"single_security_concentration", "portfolio_concentration", "sector_concentration", "currency_concentration"} <= codes
    assert all(alert["decision"] for alert in response["concentration_alerts"])


def test_empty_input_has_stable_zero_contract() -> None:
    response = build_allocation_response([], [], as_of=date(2026, 6, 12))

    assert response["total_current_value"] == 0
    assert response["included_portfolio_count"] == 0
    assert response["concentration"]["effective_number_of_holdings"] == 0
    assert response["allocation"]["security"] == []
    assert any("No positive current position values" in warning for warning in response["data_quality"]["warnings"])


def test_repository_mappings_resolve_cad_usd_and_crypto_metadata() -> None:
    cad = resolved_instrument_metadata("RY", "stock", {}, {})
    usd = resolved_instrument_metadata("NVDA", "stock", {}, {})
    crypto = resolved_instrument_metadata("BTCUSD", "crypto", {}, {})
    unknown = resolved_instrument_metadata("UNKNOWN", "", {}, {})

    assert cad == {"asset_type": "stock", "sector": "Financials", "currency": "CAD"}
    assert usd == {"asset_type": "stock", "sector": "Semiconductors - Chip Design", "currency": "USD"}
    assert crypto == {"asset_type": "crypto", "sector": "Crypto", "currency": "USD"}
    assert unknown == {"asset_type": UNKNOWN, "sector": UNKNOWN, "currency": UNKNOWN}


def test_field_level_coverage_distinguishes_missing_sector() -> None:
    response = build_allocation_response(
        [
            portfolio("Mapped", [{"ticker": "NVDA", "security_type": "stock", "current_value": 75}]),
            portfolio("Partial", [{"ticker": "UNMAPPED", "security_type": "stock", "current_value": 25}]),
        ],
        [],
        as_of=date(2026, 6, 12),
    )

    coverage = response["metadata_coverage"]
    assert coverage["asset_type_value_pct"] == 100
    assert coverage["currency_value_pct"] == 100
    assert coverage["sector_value_pct"] == 75
    assert coverage["complete_value_pct"] == 75


def test_unique_ticker_metadata_resolves_when_position_type_is_missing() -> None:
    response = build_allocation_response(
        [portfolio("Model", [{"ticker": "AAA", "current_value": 100}])],
        METADATA,
        as_of=date(2026, 6, 12),
    )
    assert response["metadata_coverage"]["complete_value_pct"] == 100
    assert response["allocation"]["asset_type"][0]["name"] == "stock"
