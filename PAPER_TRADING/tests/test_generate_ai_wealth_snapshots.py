from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.basket_service import custom_basket_response  # noqa: E402
from generate_ai_wealth_snapshots import build_markdown_report, write_operations_outputs  # noqa: E402


def test_ai_wealth_model_baskets_are_registered() -> None:
    baskets = custom_basket_response(include_archived=False)["baskets"]
    ids = {str(row["basket_id"]) for row in baskets}

    assert "ai-wealth-core" in ids
    assert "ai-wealth-growth" in ids
    assert "ai-wealth-defensive-income" in ids
    assert "ai-wealth-tactical-ai" in ids


def test_markdown_report_contains_disclaimer_and_candidate_table() -> None:
    payload = {
        "from_date": "2026-01-31",
        "to_date": "2026-06-12",
        "latest_available_date": "2026-06-12",
        "positioning": {
            "recommended_claim": "CFA-led, human-supervised, AI-assisted portfolio research and risk intelligence.",
        },
        "business_readiness": {
            "score": 72.0,
            "stage": "advisor_demo_ready",
        },
        "disclaimer": "Research workspace output only.",
        "theme_opportunities": [
            {
                "theme": "Software",
                "candidate_count": 1,
                "model_candidates": 1,
                "high_risk_count": 0,
                "average_score": 88.5,
                "top_tickers": ["MSFT"],
            }
        ],
        "ai_signal_candidates": [
            {
                "ticker": "MSFT",
                "sector": "Software",
                "score": 88.5,
                "signal": "fresh",
                "risk_bucket": "satellite",
                "suggested_action": "model_candidate",
                "five_day_change_pct": 4.2,
                "monthly_change_pct": 10.0,
                "drivers": ["fresh technical signal"],
            }
        ],
        "risk_controls": ["Human review required."],
        "next_build_steps": ["Create fact sheets."],
    }
    report = build_markdown_report(
        payload,
        [
            {
                "name": "AI Wealth Core Model",
                "role": "model_theme",
                "member_count": 7,
                "return_pct": 5.2,
                "benchmark_return_pct": 4.0,
                "alpha_pct": 1.2,
                "warning": "",
            }
        ],
    )

    assert "# AI Wealth Intelligence Snapshot" in report
    assert "Research workspace output only." in report
    assert "MSFT" in report
    assert "AI Wealth Core Model" in report


def test_write_operations_outputs_creates_proposal_and_review_files(tmp_path: Path) -> None:
    paths = write_operations_outputs(
        tmp_path,
        "snapshot",
        {
            "proposal_matrix": [
                {
                    "profile": {
                        "profile_id": "balanced-growth",
                        "profile_name": "Balanced Growth",
                    },
                    "review_status": "ready_for_internal_review",
                    "proposal_return_pct": 6.1,
                    "proposal_alpha_pct": 1.2,
                    "allocation_count": 3,
                    "policy_warnings": [],
                    "next_best_actions": ["Review"],
                }
            ],
            "advisor_review_queue": [
                {
                    "priority": "high",
                    "task_type": "data_review",
                    "subject": "TEST",
                    "source": "unit",
                    "detail": "bad price",
                }
            ],
            "ai_command_workbench": [
                {
                    "command_id": "meeting-prep",
                    "title": "Meeting Prep",
                    "category": "client_workflow",
                    "trigger": "before meeting",
                    "required_context": "profile",
                    "output_type": "brief",
                    "guardrail": "research only",
                    "generated_prompt": "Prepare a brief.",
                    "execution_mode": "copy_to_ai_tool",
                }
            ],
        },
    )

    assert paths["operations_json"].exists()
    assert paths["proposals_csv"].exists()
    assert paths["review_queue_csv"].exists()
    assert paths["ai_commands_csv"].exists()
    assert "balanced-growth" in paths["proposals_csv"].read_text(encoding="utf-8")
