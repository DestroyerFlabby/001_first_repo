from __future__ import annotations

from datetime import date
from statistics import median


SCHEMA_VERSION = "1.0"
CALCULATION_VERSION = "strategy-selector-1.0"
NO_ORDER_BEHAVIOR = "read_only_no_orders"


def number(value: object, default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def normalize(value: float, values: list[float], *, higher_is_better: bool = True) -> float:
    if not values:
        return 50.0
    low = min(values)
    high = max(values)
    if abs(high - low) < 1e-9:
        return 50.0
    score = (value - low) / (high - low) * 100
    return clamp(score if higher_is_better else 100 - score)


def max_drawdown_from_series(series: list[dict[str, object]]) -> float:
    peak = 0.0
    worst = 0.0
    for row in series:
        value = number(row.get("value"))
        if value <= 0:
            continue
        peak = max(peak, value)
        if peak:
            worst = min(worst, (value - peak) / peak * 100)
    return worst


def top_five_concentration(positions: list[dict[str, object]]) -> float:
    weights = sorted((number(row.get("portfolio_weight_pct")) for row in positions), reverse=True)
    return sum(weights[:5])


def sector_concentration(positions: list[dict[str, object]]) -> float:
    sector_weights: dict[str, float] = {}
    for row in positions:
        sector = str(row.get("sector") or "Unknown / Unclassified")
        sector_weights[sector] = sector_weights.get(sector, 0.0) + number(row.get("portfolio_weight_pct"))
    return max(sector_weights.values(), default=0.0)


def strategy_metrics(detail: dict[str, object]) -> dict[str, object]:
    positions = [row for row in detail.get("positions", []) if isinstance(row, dict)]
    realized = [row for row in detail.get("realized_positions", []) if isinstance(row, dict)]
    series = [row for row in detail.get("series", []) if isinstance(row, dict)]
    benchmark = detail.get("benchmark_comparison") if isinstance(detail.get("benchmark_comparison"), dict) else {}
    stats = detail.get("statistics") if isinstance(detail.get("statistics"), dict) else {}
    closed_returns = [number(row.get("return_pct")) for row in realized if row.get("return_pct") is not None]
    trade_count = int(number(stats.get("total_trades"), len(detail.get("trade_ledger", []) or [])))
    max_drawdown = number(benchmark.get("max_drawdown_pct"), max_drawdown_from_series(series))
    volatility = number(benchmark.get("volatility_pct"))
    return {
        "return_pct": number(detail.get("return_pct")),
        "alpha_pct": number(benchmark.get("alpha_pct")),
        "max_drawdown_pct": max_drawdown,
        "volatility_pct": volatility,
        "top_five_weight_pct": number(stats.get("top_five_weight_pct"), top_five_concentration(positions)),
        "largest_sector_weight_pct": number(
            stats.get("largest_sector_weight_pct"),
            sector_concentration(positions),
        ),
        "turnover_pct": number(stats.get("total_turnover_pct")),
        "position_count": len(positions),
        "closed_positions": len(realized),
        "trade_count": trade_count,
        "median_closed_return_pct": median(closed_returns) if closed_returns else 0.0,
        "has_next_close_execution": "next" in str(detail.get("methodology", {}).get("execution_convention", "")).casefold()
        if isinstance(detail.get("methodology"), dict)
        else False,
        "series_points": len(series),
    }


def data_quality_score(metrics: dict[str, object]) -> float:
    score = 100.0
    if number(metrics.get("series_points")) < 20:
        score -= 35
    if number(metrics.get("position_count")) < 3:
        score -= 20
    if number(metrics.get("trade_count")) < 5:
        score -= 15
    if not metrics.get("has_next_close_execution"):
        score -= 10
    return clamp(score)


def concentration_score(metrics: dict[str, object]) -> float:
    top_five = number(metrics.get("top_five_weight_pct"))
    sector = number(metrics.get("largest_sector_weight_pct"))
    return clamp(100 - max(0, top_five - 35) * 1.2 - max(0, sector - 25) * 1.5)


def scenario_resilience_score(metrics: dict[str, object]) -> float:
    drawdown = abs(number(metrics.get("max_drawdown_pct")))
    concentration = 100 - concentration_score(metrics)
    return clamp(100 - drawdown * 2.0 - concentration * 0.35)


def score_components(metrics: dict[str, object], population: dict[str, list[float]]) -> dict[str, float]:
    return {
        "normalized_return": normalize(number(metrics.get("return_pct")), population["return_pct"]),
        "normalized_alpha_vs_benchmark": normalize(number(metrics.get("alpha_pct")), population["alpha_pct"]),
        "drawdown_score": normalize(abs(number(metrics.get("max_drawdown_pct"))), population["drawdown_abs"], higher_is_better=False),
        "volatility_score": normalize(number(metrics.get("volatility_pct")), population["volatility_pct"], higher_is_better=False),
        "concentration_score": concentration_score(metrics),
        "turnover_score": normalize(number(metrics.get("turnover_pct")), population["turnover_pct"], higher_is_better=False),
        "data_quality_score": data_quality_score(metrics),
        "scenario_resilience_score": scenario_resilience_score(metrics),
    }


def weighted_score(components: dict[str, float]) -> float:
    weights = {
        "normalized_return": 0.30,
        "normalized_alpha_vs_benchmark": 0.20,
        "drawdown_score": 0.15,
        "volatility_score": 0.10,
        "concentration_score": 0.10,
        "turnover_score": 0.05,
        "data_quality_score": 0.05,
        "scenario_resilience_score": 0.05,
    }
    return sum(components[key] * weight for key, weight in weights.items())


def red_flag_penalty(metrics: dict[str, object]) -> float:
    penalty = 0.0
    if abs(number(metrics.get("max_drawdown_pct"))) > 20:
        penalty += 25
    elif abs(number(metrics.get("max_drawdown_pct"))) > 12:
        penalty += 12
    if number(metrics.get("volatility_pct")) > 30:
        penalty += 10
    if number(metrics.get("top_five_weight_pct")) > 70:
        penalty += 18
    elif number(metrics.get("top_five_weight_pct")) > 60:
        penalty += 10
    if number(metrics.get("trade_count")) < 5:
        penalty += 12
    return penalty


def strategy_warnings(metrics: dict[str, object]) -> list[str]:
    warnings: list[str] = []
    if number(metrics.get("trade_count")) < 5:
        warnings.append("Thin trade count; result may not be robust.")
    if number(metrics.get("top_five_weight_pct")) > 60:
        warnings.append("Top-five concentration exceeds 60%.")
    if number(metrics.get("largest_sector_weight_pct")) > 40:
        warnings.append("Largest sector concentration exceeds 40%.")
    if abs(number(metrics.get("max_drawdown_pct"))) > 12:
        warnings.append("Historical drawdown exceeds 12%.")
    if not metrics.get("has_next_close_execution"):
        warnings.append("Execution timing is not explicitly next-close.")
    if number(metrics.get("series_points")) < 20:
        warnings.append("Short history window; manual review required.")
    return warnings


def recommendation_status(best_id: str, ranked: list[dict[str, object]]) -> str:
    if not ranked:
        return "defer_insufficient_data"
    if any("Short history" in warning for warning in ranked[0].get("warnings", [])):
        return "manual_review_required"
    if best_id == "systematic-model-portfolio":
        return "hold_model"
    if best_id == "daily-eod-rotation-portfolio":
        return "prefer_rotation_research"
    if ranked[0]["score"] - ranked[min(1, len(ranked) - 1)]["score"] < 5:
        return "prefer_blend"
    return "prefer_core_policy" if "core" in best_id else "manual_review_required"


def draft_blend(status: str, ranked: list[dict[str, object]]) -> list[dict[str, object]]:
    if status not in {"prefer_blend", "hold_model", "prefer_rotation_research"}:
        return []
    top = {str(row["strategy_id"]): row for row in ranked[:3]}
    blend = [
        {"sleeve": "core_policy", "target_weight_pct": 65.0, "reason": "Keep most exposure in policy/core allocation."},
        {"sleeve": "systematic-model-portfolio", "target_weight_pct": 20.0, "reason": "Bounded model sleeve for point-in-time signal research."},
        {"sleeve": "daily-eod-rotation-portfolio", "target_weight_pct": 10.0, "reason": "Small tactical sleeve due to higher turnover/path risk."},
        {"sleeve": "social_signal_research", "target_weight_pct": 5.0, "reason": "Capped social/news sleeve; requires human review."},
    ]
    if status == "hold_model" and "systematic-model-portfolio" in top:
        blend[1]["target_weight_pct"] = 25.0
        blend[0]["target_weight_pct"] = 60.0
    if status == "prefer_rotation_research" and "daily-eod-rotation-portfolio" in top:
        blend[2]["target_weight_pct"] = 10.0
        blend[1]["target_weight_pct"] = 15.0
        blend[0]["target_weight_pct"] = 70.0
    return blend


def strategy_selector_response(
    start: date,
    end: date,
    strategy_details: list[dict[str, object]],
    *,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    metric_rows = []
    for detail in strategy_details:
        strategy_id = str(detail.get("portfolio_name") or detail.get("investor") or "").strip()
        if not strategy_id:
            continue
        metrics = strategy_metrics(detail)
        metric_rows.append({"strategy_id": strategy_id, "label": str(detail.get("label") or strategy_id), "metrics": metrics})

    population = {
        "return_pct": [number(row["metrics"].get("return_pct")) for row in metric_rows],
        "alpha_pct": [number(row["metrics"].get("alpha_pct")) for row in metric_rows],
        "drawdown_abs": [abs(number(row["metrics"].get("max_drawdown_pct"))) for row in metric_rows],
        "volatility_pct": [number(row["metrics"].get("volatility_pct")) for row in metric_rows],
        "turnover_pct": [number(row["metrics"].get("turnover_pct")) for row in metric_rows],
    }
    ranked: list[dict[str, object]] = []
    for row in metric_rows:
        components = score_components(row["metrics"], population)
        warnings = strategy_warnings(row["metrics"])
        raw_score = weighted_score(components)
        ranked.append(
            {
                "strategy_id": row["strategy_id"],
                "label": row["label"],
                "score": round(clamp(raw_score - red_flag_penalty(row["metrics"])), 2),
                "raw_score": round(raw_score, 2),
                "red_flag_penalty": round(red_flag_penalty(row["metrics"]), 2),
                "score_components": {key: round(value, 2) for key, value in components.items()},
                "metrics": row["metrics"],
                "warnings": warnings,
                "review_action": "manual_review" if warnings else "eligible_for_research_review",
            }
        )
    ranked.sort(key=lambda row: (-number(row.get("score")), str(row.get("strategy_id"))))
    best_id = str(ranked[0]["strategy_id"]) if ranked else ""
    status = recommendation_status(best_id, ranked)
    warnings = sorted({warning for row in ranked for warning in row.get("warnings", [])})
    return {
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "wealthsimple_fx_fees_enabled": apply_wealthsimple_fx_fees,
        "recommendation_status": status,
        "recommended_strategy": best_id or None,
        "recommended_action": {
            "hold_model": "Keep the systematic model as the primary research strategy, subject to policy sleeve caps.",
            "prefer_blend": "Use a conservative blend rather than relying on one strategy.",
            "prefer_rotation_research": "Review the rotation strategy as a tactical sleeve only; turnover and drawdown controls still apply.",
            "prefer_core_policy": "Prefer core policy allocation until research strategies show stronger risk-adjusted evidence.",
            "defer_insufficient_data": "Defer selection because comparable data is insufficient.",
            "manual_review_required": "Manual review required before changing research allocation.",
        }.get(status, "Manual review required."),
        "ranked_strategies": ranked,
        "draft_blend": draft_blend(status, ranked),
        "warnings": warnings,
        "assumptions": [
            "Research-only strategy comparison; not suitability advice.",
            "No broker orders, ledger rows, or allocation changes are created.",
            "Scores are normalized within the candidate set and can change as candidates are added.",
            "High returns are penalized when drawdown, concentration, turnover, or data quality are weak.",
        ],
        "data_quality": {
            "candidate_count": len(ranked),
            "write_behavior": NO_ORDER_BEHAVIOR,
            "manual_review_required": status in {"manual_review_required", "defer_insufficient_data"},
        },
    }
