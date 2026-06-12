from __future__ import annotations

import sys
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.wealth_intelligence_service import build_candidates, wealth_intelligence_response


def stock_row(ticker: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": ticker,
        "security_type": "stock",
        "sector": "Software",
        "return_pct": 12,
        "daily_change_pct": 1.5,
        "five_day_change_pct": 6,
        "monthly_change_pct": 16,
        "signal": {
            "classification": "strict",
            "fresh_priority": True,
            "overall_score": 82,
            "five_day_relative_strength_pct": 8,
            "five_day_volume_ratio": 2.2,
            "distance_to_20d_high_pct": 4,
        },
        "wealthsimple": {"availability": "likely-supported"},
    }
    row.update(overrides)
    return row


def test_build_candidates_scores_fresh_signals_as_model_candidates() -> None:
    candidates = build_candidates(
        [
            stock_row("AAA"),
            stock_row(
                "BBB",
                signal={"classification": "none"},
                return_pct=-4,
                monthly_change_pct=-8,
            ),
        ]
    )

    assert candidates[0]["ticker"] == "AAA"
    assert candidates[0]["suggested_action"] == "model_candidate"
    assert candidates[0]["score"] > candidates[1]["score"]
    assert candidates[0]["risk_bucket"] == "satellite"


def test_build_candidates_flags_crypto_and_large_moves_for_risk_review() -> None:
    candidates = build_candidates(
        [
            stock_row(
                "BTCUSD",
                security_type="crypto",
                sector="Crypto",
                monthly_change_pct=42,
            )
        ]
    )

    assert candidates[0]["risk_bucket"] == "high"
    assert candidates[0]["suggested_action"] == "risk_review"


def test_build_candidates_routes_extreme_data_moves_to_data_review() -> None:
    candidates = build_candidates(
        [
            stock_row(
                "SPLT",
                daily_change_pct=400,
                monthly_change_pct=35,
            )
        ]
    )

    assert candidates[0]["suggested_action"] == "data_review"
    assert "extreme_daily_move_check_split_or_bad_price" in candidates[0]["data_quality_flags"]


def test_wealth_intelligence_response_is_research_only() -> None:
    payload = wealth_intelligence_response(
        {
            "stocks": [stock_row("AAA")],
            "dashboard_metrics": {"signal_mix": {"fresh": 1, "strict": 0}},
            "latest_available_date": "2026-06-10",
        },
        {
            "baskets": [
                {
                    "basket_id": "ai-infrastructure",
                    "basket_name": "AI Infrastructure",
                    "status": "active",
                    "benchmark": "SPY",
                    "member_count": 5,
                    "rebalance_frequency": "monthly",
                    "notes": "AI basket",
                }
            ]
        },
        date(2026, 1, 1),
        date(2026, 6, 10),
    )

    assert "personalized investment advice" in payload["disclaimer"]
    assert "broker orders" in payload["disclaimer"]
    assert payload["model_baskets"][0]["role"] == "model_theme"
    assert payload["positioning"]["recommended_claim"].startswith("CFA-led")
    assert any(row["category"] == "Canadian AI governance" for row in payload["market_context"])
    assert any("human-supervised" in row["product_implication"] for row in payload["market_context"])
