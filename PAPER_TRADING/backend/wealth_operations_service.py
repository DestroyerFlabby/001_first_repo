from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from backend.basket_service import basket_performance, custom_basket_response
from backend.wealth_intelligence_service import decimal_value


ROOT = Path(__file__).resolve().parents[1]
PROFILE_FILE = ROOT / "data" / "wealth_client_profiles.csv"
ALLOCATION_FILE = ROOT / "data" / "wealth_model_allocations.csv"
COMMAND_FILE = ROOT / "data" / "wealth_ai_commands.csv"
PROFILE_FIELDS = [
    "profile_id",
    "profile_name",
    "status",
    "risk_tolerance",
    "time_horizon_years",
    "primary_objective",
    "liquidity_need",
    "max_tactical_pct",
    "max_single_theme_pct",
    "min_cash_pct",
    "notes",
]
ALLOCATION_FIELDS = [
    "profile_id",
    "basket_id",
    "target_weight",
    "allocation_role",
    "rationale",
]
COMMAND_FIELDS = [
    "command_id",
    "title",
    "category",
    "trigger",
    "required_context",
    "output_type",
    "guardrail",
    "prompt_template",
]
OPERATING_MODULES = [
    {
        "module": "Client intake and policy profile",
        "status": "configured",
        "description": "Structured demo profiles capture objective, risk tolerance, horizon, liquidity, tactical limits, and cash minimums.",
    },
    {
        "module": "Model portfolio library",
        "status": "configured",
        "description": "AI Wealth model baskets and existing theme baskets are available for proposal construction and performance checks.",
    },
    {
        "module": "AI research and candidate ranking",
        "status": "configured",
        "description": "Signal candidates are scored with explainable technical, relative-strength, volume, risk, and data-quality drivers.",
    },
    {
        "module": "Policy-fit proposal matrix",
        "status": "configured",
        "description": "Profiles map to target model allocations with policy warnings for high tactical or alternative exposure.",
    },
    {
        "module": "Advisor review queue",
        "status": "configured",
        "description": "Data-review flags, risk-review candidates, and policy exceptions become human review tasks.",
    },
    {
        "module": "Client-ready reporting",
        "status": "partial",
        "description": "Markdown/CSV/JSON snapshots exist; PDF-style fact sheets and meeting packets are the next export layer.",
    },
    {
        "module": "Compliance and registration workflow",
        "status": "external_required",
        "description": "Registration, suitability, KYC, custody, order management, and client advice require a registered firm or legal setup.",
    },
]
GOVERNANCE_CHECKLIST = [
    "AI outputs must be dated and reproducible from source data.",
    "Every model candidate must retain visible signal, risk, and data-quality drivers.",
    "Human review is required before external use of candidate, model, or proposal output.",
    "Client profile proposals are policy-fit research drafts, not personalized investment advice.",
    "Marketing language must say AI-assisted and human-supervised unless a registered process supports stronger claims.",
    "Performance output must distinguish simulated/backtested results from live audited performance.",
]


def read_csv(path: Path, fields: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            raise ValueError(f"{path.name} has unexpected columns")
        return list(reader)


def normalize_pct(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def read_profiles(include_research: bool = True) -> list[dict[str, Any]]:
    rows = []
    for row in read_csv(PROFILE_FILE, PROFILE_FIELDS):
        normalized = {field: str(row.get(field) or "").strip() for field in PROFILE_FIELDS}
        normalized["profile_id"] = normalized["profile_id"].casefold()
        normalized["status"] = normalized["status"].casefold()
        normalized["time_horizon_years"] = int(normalized["time_horizon_years"] or "0")
        normalized["max_tactical_pct"] = float(normalize_pct(normalized["max_tactical_pct"]))
        normalized["max_single_theme_pct"] = float(normalize_pct(normalized["max_single_theme_pct"]))
        normalized["min_cash_pct"] = float(normalize_pct(normalized["min_cash_pct"]))
        if normalized["status"] == "research" and not include_research:
            continue
        rows.append(normalized)
    return rows


def read_allocations() -> list[dict[str, Any]]:
    rows = []
    for row in read_csv(ALLOCATION_FILE, ALLOCATION_FIELDS):
        normalized = {field: str(row.get(field) or "").strip() for field in ALLOCATION_FIELDS}
        normalized["profile_id"] = normalized["profile_id"].casefold()
        normalized["basket_id"] = normalized["basket_id"].casefold()
        normalized["target_weight"] = float(normalize_pct(normalized["target_weight"]))
        rows.append(normalized)
    return rows


def read_ai_commands() -> list[dict[str, Any]]:
    rows = []
    for row in read_csv(COMMAND_FILE, COMMAND_FIELDS):
        normalized = {field: str(row.get(field) or "").strip() for field in COMMAND_FIELDS}
        normalized["command_id"] = normalized["command_id"].casefold()
        rows.append(normalized)
    return rows


def basket_performance_map(start: date, end: date) -> dict[str, dict[str, Any]]:
    baskets = custom_basket_response(include_archived=False)["baskets"]
    performances: dict[str, dict[str, Any]] = {}
    for basket in baskets:
        basket_id = str(basket["basket_id"])
        try:
            performance = basket_performance(basket_id, start, end)
            performances[basket_id] = {
                "return_pct": performance.get("return_pct"),
                "benchmark_return_pct": performance.get("benchmark_return_pct"),
                "alpha_pct": performance.get("alpha_pct"),
                "member_count": basket.get("member_count"),
                "name": basket.get("basket_name"),
                "status": basket.get("status"),
                "warning": "",
            }
        except Exception as exc:
            performances[basket_id] = {
                "return_pct": None,
                "benchmark_return_pct": None,
                "alpha_pct": None,
                "member_count": basket.get("member_count"),
                "name": basket.get("basket_name"),
                "status": basket.get("status"),
                "warning": str(exc),
            }
    return performances


def command_context(
    wealth_payload: dict[str, Any],
    proposals: list[dict[str, Any]],
    review_tasks: list[dict[str, Any]],
    start: date,
    end: date,
) -> dict[str, str]:
    ready_profiles = [
        row["profile"]["profile_name"]
        for row in proposals
        if row["review_status"] == "ready_for_internal_review"
    ]
    first_proposal = proposals[0] if proposals else {"profile": {}, "allocations": []}
    top_basket = next(iter(wealth_payload.get("model_basket_performance", []) or []), {})
    high_priority_tasks = [
        f"{row['task_type']}:{row['subject']}"
        for row in review_tasks
        if row.get("priority") == "high"
    ]
    medium_priority_tasks = [
        f"{row['task_type']}:{row['subject']}"
        for row in review_tasks
        if row.get("priority") == "medium"
    ]
    data_review_tickers = [
        str(row.get("ticker"))
        for row in wealth_payload.get("ai_signal_candidates", [])
        if row.get("suggested_action") == "data_review"
    ]
    top_candidates = [
        str(row.get("ticker"))
        for row in wealth_payload.get("ai_signal_candidates", [])[:8]
    ]
    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "profile_name": str(first_proposal.get("profile", {}).get("profile_name") or "selected profile"),
        "proposal_return_pct": str(first_proposal.get("proposal_return_pct", "n/a")),
        "proposal_alpha_pct": str(first_proposal.get("proposal_alpha_pct", "n/a")),
        "allocations": "; ".join(
            f"{row['basket_id']} {row['target_weight']}%"
            for row in first_proposal.get("allocations", [])
        )
        or "selected model allocations",
        "policy_warnings": "; ".join(first_proposal.get("policy_warnings", [])) or "none",
        "high_priority_tasks": "; ".join(high_priority_tasks) or "none",
        "medium_priority_tasks": "; ".join(medium_priority_tasks) or "none",
        "data_review_tickers": ", ".join(data_review_tickers) or "none",
        "governance_checklist": "; ".join(GOVERNANCE_CHECKLIST),
        "basket_name": str(top_basket.get("name") or top_basket.get("basket_id") or "selected model basket"),
        "top_candidates": ", ".join(top_candidates) or "none",
        "ready_profiles": ", ".join(ready_profiles) or "none",
        "review_task_count": str(len(review_tasks)),
    }


def render_prompt(template: str, context: dict[str, str]) -> str:
    prompt = template
    for key, value in context.items():
        prompt = prompt.replace("{" + key + "}", value)
    return prompt


def ai_command_workbench(
    wealth_payload: dict[str, Any],
    proposals: list[dict[str, Any]],
    review_tasks: list[dict[str, Any]],
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    context = command_context(wealth_payload, proposals, review_tasks, start, end)
    commands = []
    for command in read_ai_commands():
        commands.append(
            {
                **command,
                "generated_prompt": render_prompt(str(command["prompt_template"]), context),
                "available": True,
                "execution_mode": "copy_to_ai_tool",
            }
        )
    return commands


def proposal_policy_warnings(
    profile: dict[str, Any],
    allocations: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    total_weight = sum(decimal_value(row["target_weight"]) for row in allocations)
    if total_weight != Decimal("100"):
        warnings.append(f"target weights sum to {total_weight}% instead of 100%")
    tactical_weight = sum(
        decimal_value(row["target_weight"])
        for row in allocations
        if "tactical" in str(row.get("allocation_role") or "")
    )
    if tactical_weight > decimal_value(profile["max_tactical_pct"]):
        warnings.append(f"tactical sleeve {tactical_weight}% exceeds policy max {profile['max_tactical_pct']}%")
    for row in allocations:
        weight = decimal_value(row["target_weight"])
        if weight > decimal_value(profile["max_single_theme_pct"]):
            warnings.append(
                f"{row['basket_id']} weight {weight}% exceeds single-theme max {profile['max_single_theme_pct']}%"
            )
    alternative_weight = sum(
        decimal_value(row["target_weight"])
        for row in allocations
        if "alternative" in str(row.get("allocation_role") or "")
    )
    if alternative_weight and profile["risk_tolerance"] not in {"high", "very_high"}:
        warnings.append("alternative sleeve appears in a non-high-risk profile")
    return warnings


def proposal_matrix(start: date, end: date) -> list[dict[str, Any]]:
    profiles = read_profiles(include_research=True)
    allocations = read_allocations()
    grouped_allocations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in allocations:
        grouped_allocations[str(row["profile_id"])].append(row)
    performance = basket_performance_map(start, end)

    proposals: list[dict[str, Any]] = []
    for profile in profiles:
        rows = grouped_allocations.get(str(profile["profile_id"]), [])
        weighted_return = Decimal("0")
        weighted_alpha = Decimal("0")
        allocation_rows = []
        for row in rows:
            basket = performance.get(str(row["basket_id"]), {})
            weight = decimal_value(row["target_weight"])
            basket_return = decimal_value(basket.get("return_pct"))
            basket_alpha = decimal_value(basket.get("alpha_pct"))
            weighted_return += basket_return * weight / Decimal("100")
            weighted_alpha += basket_alpha * weight / Decimal("100")
            allocation_rows.append(
                {
                    **row,
                    "basket_name": basket.get("name") or row["basket_id"],
                    "basket_return_pct": float(basket_return),
                    "basket_alpha_pct": float(basket_alpha),
                    "weighted_return_contribution_pct": float(basket_return * weight / Decimal("100")),
                    "warning": basket.get("warning", ""),
                }
            )
        warnings = proposal_policy_warnings(profile, rows)
        proposals.append(
            {
                "profile": profile,
                "proposal_return_pct": round(float(weighted_return), 6),
                "proposal_alpha_pct": round(float(weighted_alpha), 6),
                "allocation_count": len(allocation_rows),
                "allocations": allocation_rows,
                "policy_warnings": warnings,
                "review_status": "needs_review" if warnings or profile["status"] == "research" else "ready_for_internal_review",
                "next_best_actions": proposal_actions(profile, warnings),
            }
        )
    return proposals


def proposal_actions(profile: dict[str, Any], warnings: list[str]) -> list[str]:
    actions = [
        "Generate meeting-prep packet using current model-basket performance.",
        "Confirm risk tolerance, time horizon, liquidity need, and constraints before any external use.",
        "Document human approval and dated source data for the proposal.",
    ]
    if warnings:
        actions.insert(0, "Resolve policy warnings before using this profile in an advisor demo.")
    if profile["status"] == "research":
        actions.insert(0, "Keep this profile in research mode until a reviewer approves the policy limits.")
    return actions


def advisor_review_queue(wealth_payload: dict[str, Any], proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for row in wealth_payload.get("ai_signal_candidates", []):
        action = str(row.get("suggested_action") or "")
        if action in {"data_review", "risk_review"}:
            tasks.append(
                {
                    "priority": "high" if action == "data_review" else "medium",
                    "task_type": action,
                    "subject": row.get("ticker"),
                    "source": "ai_signal_candidates",
                    "detail": "; ".join(row.get("data_quality_flags") or row.get("drivers") or []),
                }
            )
    for proposal in proposals:
        for warning in proposal["policy_warnings"]:
            tasks.append(
                {
                    "priority": "high",
                    "task_type": "policy_warning",
                    "subject": proposal["profile"]["profile_id"],
                    "source": "proposal_matrix",
                    "detail": warning,
                }
            )
    priority_order = {"high": 0, "medium": 1, "low": 2}
    tasks.sort(key=lambda row: (priority_order.get(str(row["priority"]), 9), str(row["subject"])))
    return tasks


def wealth_operations_response(
    wealth_payload: dict[str, Any],
    start: date,
    end: date,
) -> dict[str, Any]:
    proposals = proposal_matrix(start, end)
    review_tasks = advisor_review_queue(wealth_payload, proposals)
    command_rows = ai_command_workbench(wealth_payload, proposals, review_tasks, start, end)
    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "operating_modules": OPERATING_MODULES,
        "governance_checklist": GOVERNANCE_CHECKLIST,
        "client_profiles": read_profiles(include_research=True),
        "proposal_matrix": proposals,
        "advisor_review_queue": review_tasks,
        "ai_command_workbench": command_rows,
        "summary": {
            "profile_count": len(proposals),
            "ready_profile_count": sum(row["review_status"] == "ready_for_internal_review" for row in proposals),
            "review_task_count": len(review_tasks),
            "high_priority_task_count": sum(row["priority"] == "high" for row in review_tasks),
            "ai_command_count": len(command_rows),
        },
        "disclaimer": (
            "Operational research workflow only. Client profiles are demo policy profiles and do not represent "
            "personalized advice, suitability approval, account opening, custody, or order execution."
        ),
    }
