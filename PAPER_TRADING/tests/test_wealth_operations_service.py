from __future__ import annotations

import sys
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.wealth_operations_service import (  # noqa: E402
    ai_command_workbench,
    proposal_policy_warnings,
    read_ai_commands,
    read_allocations,
    read_profiles,
    wealth_operations_response,
)


def test_profiles_and_allocations_are_configured() -> None:
    profiles = read_profiles(include_research=True)
    allocations = read_allocations()

    assert {row["profile_id"] for row in profiles} >= {
        "capital-preservation",
        "balanced-growth",
        "ai-growth",
        "opportunistic-ai",
    }
    assert any(row["basket_id"] == "ai-wealth-core" for row in allocations)


def test_policy_warnings_detect_theme_limit_breaches() -> None:
    warnings = proposal_policy_warnings(
        {
            "max_tactical_pct": 10.0,
            "max_single_theme_pct": 25.0,
            "risk_tolerance": "medium",
        },
        [
            {"basket_id": "ai-wealth-growth", "target_weight": 60, "allocation_role": "growth_core"},
            {"basket_id": "ai-wealth-tactical-ai", "target_weight": 40, "allocation_role": "tactical_ai"},
        ],
    )

    assert any("exceeds single-theme max" in warning for warning in warnings)
    assert any("tactical sleeve" in warning for warning in warnings)


def test_wealth_operations_response_contains_review_queue() -> None:
    response = wealth_operations_response(
        {
            "ai_signal_candidates": [
                {
                    "ticker": "TEST",
                    "suggested_action": "data_review",
                    "data_quality_flags": ["bad_price"],
                }
            ]
        },
        date(2026, 1, 31),
        date(2026, 6, 11),
    )

    assert response["summary"]["profile_count"] >= 4
    assert response["summary"]["review_task_count"] >= 1
    assert any(row["subject"] == "TEST" for row in response["advisor_review_queue"])


def test_ai_commands_are_registered_and_hydrated() -> None:
    commands = read_ai_commands()
    workbench = ai_command_workbench(
        {
            "ai_signal_candidates": [
                {"ticker": "MSFT", "suggested_action": "model_candidate"},
            ],
            "model_basket_performance": [
                {"name": "AI Wealth Core Model"},
            ],
        },
        [
            {
                "profile": {"profile_name": "Balanced Growth Demo"},
                "proposal_return_pct": 8.1,
                "proposal_alpha_pct": 1.2,
                "allocations": [{"basket_id": "ai-wealth-core", "target_weight": 55}],
                "policy_warnings": [],
                "review_status": "ready_for_internal_review",
            }
        ],
        [],
        date(2026, 1, 31),
        date(2026, 6, 11),
    )

    assert len(commands) >= 8
    assert any(row["command_id"] == "meeting-prep" for row in workbench)
    meeting_prep = next(row for row in workbench if row["command_id"] == "meeting-prep")
    assert "Balanced Growth Demo" in meeting_prep["generated_prompt"]
    assert "{profile_name}" not in meeting_prep["generated_prompt"]
