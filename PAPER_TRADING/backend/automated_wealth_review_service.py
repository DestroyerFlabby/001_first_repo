from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.rebalance_service import rebalance_preview


SCHEMA_VERSION = "1.0"
CALCULATION_VERSION = "automated-wealth-review-1.0"
NO_ORDER_BEHAVIOR = "read_only_no_orders"


def number(value: object, default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def allocation_health(allocation_payload: dict[str, object]) -> dict[str, object]:
    coverage = allocation_payload.get("metadata_coverage") if isinstance(allocation_payload.get("metadata_coverage"), dict) else {}
    concentration = allocation_payload.get("concentration") if isinstance(allocation_payload.get("concentration"), dict) else {}
    alerts = allocation_payload.get("concentration_alerts") if isinstance(allocation_payload.get("concentration_alerts"), list) else []
    blockers: list[str] = []
    warnings: list[str] = []
    complete = number(coverage.get("complete_value_pct"), 0)
    asset_type = number(coverage.get("asset_type_value_pct"), 0)
    if complete < 75:
        blockers.append(f"Complete metadata coverage is {complete:.1f}%, below 75%.")
    if asset_type < 90:
        blockers.append(f"Asset-type metadata coverage is {asset_type:.1f}%, below 90%.")
    if number(concentration.get("top_position_weight_pct")) > 10:
        warnings.append("Largest security exceeds 10% of tracked value.")
    if number(concentration.get("top_five_weight_pct")) > 60:
        warnings.append("Top-five concentration exceeds 60% of tracked value.")
    warnings.extend(str(alert.get("message")) for alert in alerts if isinstance(alert, dict) and alert.get("message"))
    return {
        "complete_metadata_pct": complete,
        "asset_type_metadata_pct": asset_type,
        "top_position_weight_pct": number(concentration.get("top_position_weight_pct")),
        "top_five_weight_pct": number(concentration.get("top_five_weight_pct")),
        "blockers": blockers,
        "warnings": sorted(set(warnings)),
    }


def risk_health(risk_payload: dict[str, object] | None) -> dict[str, object]:
    if not risk_payload:
        return {"status": "not_evaluated", "blockers": [], "warnings": ["Risk detail not supplied for automated review."]}
    metrics = risk_payload.get("metrics") if isinstance(risk_payload.get("metrics"), dict) else {}
    alerts = risk_payload.get("alerts") if isinstance(risk_payload.get("alerts"), list) else []
    warnings: list[str] = []
    if abs(number(metrics.get("current_drawdown_pct"))) > 8:
        warnings.append("Current drawdown exceeds 8%.")
    if abs(number(metrics.get("max_drawdown_pct"))) > 12:
        warnings.append("Maximum drawdown exceeds 12%.")
    warnings.extend(str(alert.get("message")) for alert in alerts if isinstance(alert, dict) and alert.get("message"))
    return {"status": "evaluated", "blockers": [], "warnings": sorted(set(warnings)), "metrics": metrics}


def current_weights_valid(current_weights: list[dict[str, object]]) -> tuple[bool, str]:
    if not current_weights:
        return False, "Explicit current policy-sleeve weights are required before draft rebalancing."
    total = sum(number(row.get("current_weight")) for row in current_weights)
    if abs(total - 100) > 0.01:
        return False, f"Current policy-sleeve weights sum to {total:.2f}%, not 100%."
    return True, ""


def decision_status(allocation: dict[str, object], risk: dict[str, object], rebalance: dict[str, object] | None) -> str:
    if allocation["blockers"]:
        return "data_quality_review_required"
    if risk.get("status") == "evaluated" and risk["warnings"]:
        return "risk_review_required"
    if rebalance and any(abs(number(row.get("proposed_dollar_change"))) > 0 for row in rebalance.get("allocations", [])):
        return "rebalance_review_required"
    if not rebalance:
        return "policy_profile_required"
    return "no_action_required"


def automated_wealth_review_response(
    start: date,
    end: date,
    allocation_payload: dict[str, object],
    *,
    profile_id: str = "balanced-growth",
    current_weights: list[dict[str, object]] | None = None,
    portfolio_value: Decimal = Decimal("100000"),
    risk_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    allocation = allocation_health(allocation_payload)
    risk = risk_health(risk_payload)
    valid_weights, blocked_reason = current_weights_valid(current_weights or [])
    rebalance_payload: dict[str, object] | None = None
    rebalance_blockers: list[str] = []
    if valid_weights and not allocation["blockers"]:
        try:
            rebalance_payload = rebalance_preview(profile_id, current_weights or [], portfolio_value)
        except ValueError as exc:
            rebalance_blockers.append(str(exc))
    elif blocked_reason:
        rebalance_blockers.append(blocked_reason)
    status = decision_status(allocation, risk, rebalance_payload)
    if rebalance_blockers and status == "no_action_required":
        status = "manual_review_required"
    if rebalance_blockers and status == "policy_profile_required":
        status = "policy_profile_required"
    next_action = {
        "no_action_required": "No automated action is required; keep monitoring the selected window.",
        "rebalance_review_required": "Review the draft rebalance output before taking any action.",
        "risk_review_required": "Review risk breaches before changing allocations.",
        "data_quality_review_required": "Improve metadata coverage before relying on automation.",
        "policy_profile_required": "Select or enter explicit policy-sleeve weights before draft rebalancing.",
        "manual_review_required": "Manual review is required before proceeding.",
    }.get(status, "Manual review is required before proceeding.")
    return {
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "review_status": status,
        "profile_id": profile_id,
        "next_review_action": next_action,
        "allocation_health": allocation,
        "risk_health": risk,
        "rebalance_health": {
            "draft_available": rebalance_payload is not None,
            "blockers": rebalance_blockers,
            "draft": rebalance_payload,
        },
        "warnings": sorted(set([*allocation["warnings"], *risk["warnings"], *rebalance_blockers])),
        "assumptions": [
            "Research-only automated review; not suitability advice.",
            "No broker orders, trade ledger entries, or allocation changes are created.",
            "Draft rebalancing requires explicit current policy-sleeve weights.",
            "Unknown holdings are not silently mapped to policy sleeves.",
        ],
        "data_quality": {
            "write_behavior": NO_ORDER_BEHAVIOR,
            "source_modules": ["wealth_allocation_response", "portfolio_risk_response", "rebalance_preview"],
        },
    }
