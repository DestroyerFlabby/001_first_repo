from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from decimal import Decimal


SCHEMA_VERSION = "1.0"
CALCULATION_VERSION = "wealth-risk-2026-06-12"


def _as_float(value: Decimal) -> float:
    return round(float(value), 6)


def _returns(series: list[dict[str, object]]) -> list[tuple[str, Decimal]]:
    cleaned = sorted(
        (
            (str(row["date"]), Decimal(str(row["value"])))
            for row in series
            if row.get("date") and row.get("value") is not None
        ),
        key=lambda item: item[0],
    )
    result: list[tuple[str, Decimal]] = []
    for (previous_day, previous), (day, current) in zip(cleaned, cleaned[1:]):
        del previous_day
        if previous:
            result.append((day, current / previous - 1))
    return result


def _sample_volatility(values: list[Decimal]) -> Decimal:
    if len(values) < 2:
        return Decimal("0")
    floats = [float(value) for value in values]
    mean = sum(floats) / len(floats)
    variance = sum((value - mean) ** 2 for value in floats) / (len(floats) - 1)
    return Decimal(str(math.sqrt(variance) * math.sqrt(252) * 100))


def _drawdown_metrics(series: list[dict[str, object]]) -> dict[str, object]:
    cleaned = sorted(
        (
            (date.fromisoformat(str(row["date"])), Decimal(str(row["value"])))
            for row in series
            if row.get("date") and row.get("value") is not None
        ),
        key=lambda item: item[0],
    )
    if not cleaned:
        return {
            "maximum_drawdown_pct": 0,
            "current_drawdown_pct": 0,
            "longest_recovery_sessions": 0,
            "current_underwater_sessions": 0,
            "drawdown_series": [],
        }
    peak = cleaned[0][1]
    peak_day = cleaned[0][0]
    maximum = Decimal("0")
    current_underwater = 0
    longest_recovery = 0
    drawdowns: list[dict[str, object]] = []
    for day, value in cleaned:
        if value >= peak:
            if current_underwater:
                longest_recovery = max(longest_recovery, current_underwater)
            peak = value
            peak_day = day
            current_underwater = 0
        else:
            current_underwater += 1
        drawdown = (value / peak - 1) * 100 if peak else Decimal("0")
        maximum = min(maximum, drawdown)
        drawdowns.append({"date": day.isoformat(), "drawdown_pct": _as_float(drawdown), "peak_date": peak_day.isoformat()})
    longest_recovery = max(longest_recovery, current_underwater)
    return {
        "maximum_drawdown_pct": _as_float(maximum),
        "current_drawdown_pct": drawdowns[-1]["drawdown_pct"],
        "longest_recovery_sessions": longest_recovery,
        "current_underwater_sessions": current_underwater,
        "drawdown_series": drawdowns,
    }


def _concentration(positions: list[dict[str, object]]) -> dict[str, object]:
    values = [max(Decimal(str(row.get("current_value") or 0)), Decimal("0")) for row in positions]
    total = sum(values, Decimal("0"))
    weights = [value / total for value in values if total and value > 0]
    weights.sort(reverse=True)
    hhi = sum((weight * weight for weight in weights), Decimal("0"))
    return {
        "position_count": len(weights),
        "largest_position_weight_pct": _as_float(weights[0] * 100) if weights else 0,
        "top_five_weight_pct": _as_float(sum(weights[:5], Decimal("0")) * 100),
        "effective_number_of_holdings": _as_float(Decimal("1") / hhi) if hhi else 0,
    }


def _benchmark_metrics(
    portfolio_series: list[dict[str, object]],
    benchmark_series: list[dict[str, object]],
) -> dict[str, object]:
    portfolio = dict(_returns(portfolio_series))
    benchmark = dict(_returns(benchmark_series))
    common = sorted(set(portfolio) & set(benchmark))
    if len(common) < 2:
        return {"beta": None, "tracking_error_pct": None, "aligned_sessions": len(common)}
    portfolio_values = [portfolio[day] for day in common]
    benchmark_values = [benchmark[day] for day in common]
    benchmark_mean = sum(benchmark_values, Decimal("0")) / Decimal(len(benchmark_values))
    portfolio_mean = sum(portfolio_values, Decimal("0")) / Decimal(len(portfolio_values))
    covariance = sum(
        ((portfolio_value - portfolio_mean) * (benchmark_value - benchmark_mean)
         for portfolio_value, benchmark_value in zip(portfolio_values, benchmark_values)),
        Decimal("0"),
    ) / Decimal(len(common) - 1)
    variance = sum(((value - benchmark_mean) ** 2 for value in benchmark_values), Decimal("0")) / Decimal(len(common) - 1)
    active_returns = [portfolio[day] - benchmark[day] for day in common]
    return {
        "beta": _as_float(covariance / variance) if variance else None,
        "tracking_error_pct": _as_float(_sample_volatility(active_returns)),
        "aligned_sessions": len(common),
    }


def portfolio_risk_response(
    detail: dict[str, object],
    start: date,
    end: date,
    *,
    base_currency: str = "USD",
) -> dict[str, object]:
    series = list(detail.get("series") or [])
    positions = list(detail.get("positions") or [])
    benchmark = detail.get("benchmark_comparison") if isinstance(detail.get("benchmark_comparison"), dict) else {}
    daily_returns = [value for _, value in _returns(series)]
    downside_returns = [value for value in daily_returns if value < 0]
    drawdown = _drawdown_metrics(series)
    concentration = _concentration(positions)
    relative = _benchmark_metrics(series, list(benchmark.get("benchmark_series") or []))
    warnings = [str(value) for value in detail.get("warnings") or []]
    if len(series) < 20:
        warnings.append("Fewer than 20 daily portfolio observations; volatility and drawdown confidence is low.")
    if not positions:
        warnings.append("No current position detail is available for concentration analysis.")
    if relative["aligned_sessions"] < 20:
        warnings.append("Insufficient aligned benchmark history for reliable beta and tracking error.")
    confidence = "high"
    if warnings or len(series) < 60:
        confidence = "medium"
    if len(series) < 20 or not positions:
        confidence = "low"

    alerts: list[dict[str, str]] = []
    if Decimal(str(concentration["largest_position_weight_pct"])) > Decimal("10"):
        alerts.append({"severity": "high", "type": "position_concentration", "message": "Largest position exceeds 10% of current portfolio value."})
    if Decimal(str(concentration["top_five_weight_pct"])) > Decimal("60"):
        alerts.append({"severity": "watch", "type": "top_five_concentration", "message": "Top five positions exceed 60% of current portfolio value."})
    if Decimal(str(drawdown["current_drawdown_pct"])) <= Decimal("-8"):
        alerts.append({"severity": "high", "type": "current_drawdown", "message": "Current drawdown exceeds the 8% review threshold."})
    if Decimal(str(drawdown["maximum_drawdown_pct"])) <= Decimal("-12"):
        alerts.append({"severity": "watch", "type": "maximum_drawdown", "message": "Historical drawdown exceeded the 12% tactical risk-review threshold."})

    sector_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for position in positions:
        sector_values[str(position.get("sector") or "Unclassified")] += Decimal(str(position.get("current_value") or 0))
    total_position_value = sum(sector_values.values(), Decimal("0"))
    sectors = [
        {"sector": sector, "value": _as_float(value), "weight_pct": _as_float(value / total_position_value * 100) if total_position_value else 0}
        for sector, value in sorted(sector_values.items(), key=lambda item: item[1], reverse=True)
    ]
    if sectors and Decimal(str(sectors[0]["weight_pct"])) > Decimal("30"):
        alerts.append({"severity": "high", "type": "sector_concentration", "message": f"{sectors[0]['sector']} exceeds 30% of current position value."})

    return {
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "portfolio_name": detail.get("investor") or detail.get("portfolio_name") or "portfolio",
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "as_of": str(series[-1]["date"]) if series else end.isoformat(),
        "base_currency": base_currency,
        "metrics": {
            "annualized_volatility_pct": _as_float(_sample_volatility(daily_returns)),
            "downside_deviation_pct": _as_float(_sample_volatility(downside_returns)),
            "best_day_pct": _as_float(max(daily_returns, default=Decimal("0")) * 100),
            "worst_day_pct": _as_float(min(daily_returns, default=Decimal("0")) * 100),
            **{key: value for key, value in drawdown.items() if key != "drawdown_series"},
            **concentration,
            **relative,
        },
        "drawdown_series": drawdown["drawdown_series"],
        "sector_concentration": sectors,
        "alerts": alerts,
        "data_quality": {
            "confidence": confidence,
            "series_points": len(series),
            "position_records": len(positions),
            "benchmark_aligned_sessions": relative["aligned_sessions"],
            "warnings": list(dict.fromkeys(warnings)),
            "assumptions": [
                "Close-to-close daily returns are used.",
                "Annualized statistics use 252 trading sessions.",
                "Position concentration uses current market values and does not perform ETF look-through.",
                "USD is the reporting currency unless a future household policy specifies otherwise.",
            ],
            "sources": ["Existing PAPER_TRADING portfolio series", "Yahoo close data", "Configured portfolio benchmark"],
        },
    }
