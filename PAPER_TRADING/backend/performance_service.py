from __future__ import annotations

from datetime import date
from decimal import Decimal


SCHEMA_VERSION = "1.0"
CALCULATION_VERSION = "wealth-performance-2026-06-12"


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _float(value: Decimal) -> float:
    return round(float(value), 6)


def portfolio_performance_response(
    detail: dict[str, object],
    start: date,
    end: date,
    *,
    base_currency: str = "USD",
) -> dict[str, object]:
    positions = list(detail.get("positions") or [])
    realized = list(detail.get("realized_positions") or [])
    series = list(detail.get("series") or [])
    initial_value = _decimal(detail.get("initial_value"))
    current_value = _decimal(detail.get("current_value"))
    reported_gain = _decimal(detail.get("gain_loss"))
    reported_return = _decimal(detail.get("return_pct"))
    benchmark = detail.get("benchmark_comparison") if isinstance(detail.get("benchmark_comparison"), dict) else {}

    contributors: list[dict[str, object]] = []
    unrealized_total = Decimal("0")
    for row in positions:
        if not isinstance(row, dict):
            continue
        gain = _decimal(row.get("gain_loss"))
        unrealized_total += gain
        contributors.append({
            "ticker": row.get("ticker") or "Unknown",
            "status": "open",
            "gain_loss": _float(gain),
            "return_pct": _float(_decimal(row.get("return_pct"))),
            "current_value": _float(_decimal(row.get("current_value"))),
            "contribution_pct": _float(gain / initial_value * 100) if initial_value else 0,
        })

    realized_total = Decimal("0")
    for row in realized:
        if not isinstance(row, dict):
            continue
        gain = _decimal(row.get("gain_loss"))
        realized_total += gain
        contributors.append({
            "ticker": row.get("ticker") or "Unknown",
            "status": "closed",
            "gain_loss": _float(gain),
            "return_pct": _float(_decimal(row.get("return_pct"))),
            "current_value": 0,
            "contribution_pct": _float(gain / initial_value * 100) if initial_value else 0,
        })
    contributors.sort(key=lambda row: abs(float(row["gain_loss"])), reverse=True)
    explained_gain = unrealized_total + realized_total
    residual = reported_gain - explained_gain
    tolerance = max(abs(reported_gain) * Decimal("0.01"), Decimal("1"))
    warnings = [str(value) for value in detail.get("warnings") or []]
    if abs(residual) > tolerance:
        warnings.append(
            "Position-level realized and unrealized P&L does not fully reconcile to reported portfolio gain; cash, partial sales, FX, or incomplete detail may explain the residual."
        )
    if len(series) < 2:
        warnings.append("A complete daily value series is unavailable; time-weighted path analysis is limited.")

    return {
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "portfolio_name": detail.get("investor") or detail.get("portfolio_name") or "portfolio",
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "as_of": str(series[-1]["date"]) if series else end.isoformat(),
        "base_currency": base_currency,
        "summary": {
            "initial_value": _float(initial_value),
            "current_value": _float(current_value),
            "gain_loss": _float(reported_gain),
            "return_pct": _float(reported_return),
            "benchmark": benchmark.get("benchmark") or "SPY",
            "benchmark_return_pct": benchmark.get("benchmark_return_pct", 0),
            "alpha_pct": benchmark.get("alpha_pct", 0),
            "realized_gain_loss": _float(realized_total),
            "unrealized_gain_loss": _float(unrealized_total),
            "reconciliation_residual": _float(residual),
        },
        "fixed_period_changes": {
            "daily_change_pct": detail.get("daily_change_pct"),
            "five_day_change_pct": detail.get("five_day_change_pct"),
            "monthly_change_pct": detail.get("monthly_change_pct"),
        },
        "series": series,
        "benchmark_series": list(benchmark.get("benchmark_series") or []),
        "contributions": contributors,
        "data_quality": {
            "confidence": "high" if len(series) >= 60 and abs(residual) <= tolerance else "medium" if series else "low",
            "series_points": len(series),
            "open_position_records": len(positions),
            "closed_position_records": len(realized),
            "warnings": list(dict.fromkeys(warnings)),
            "assumptions": [
                "Reported portfolio return is taken from the existing strategy or account detail service.",
                "Contribution percentage is position gain/loss divided by opening portfolio value; it is a reconciliation aid, not Brinson attribution.",
                "Money-weighted return is not calculated because complete external cash flows are unavailable.",
            ],
        },
    }
