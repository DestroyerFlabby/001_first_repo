from __future__ import annotations

from datetime import date
from typing import Callable


SCHEMA_VERSION = "1.0"
CALCULATION_VERSION = "linear-scenarios-1.0"
RECONCILIATION_TOLERANCE = 0.01
UNKNOWN = "Unknown / Unclassified"
TECHNOLOGY_TERMS = (
    "technology",
    "software",
    "semiconductor",
    "ai ",
    "ai/",
    "artificial intelligence",
    "cloud",
    "cybersecurity",
    "networking",
    "robotics",
    "data center",
)
EQUITY_ETF_TERMS = (
    "equity",
    "nasdaq",
    "s&p",
    "broad market",
    "technology",
    "infrastructure",
    "dividend",
    "growth",
)


def text(value: object) -> str:
    return str(value or "").strip()


def classified_text(value: object) -> str:
    resolved = text(value)
    return "" if resolved.casefold() in {"unknown", "unknown / unclassified", "unclassified"} else resolved


def normalized_type(position: dict[str, object]) -> str:
    return classified_text(position.get("security_type") or position.get("asset_type")).casefold()


def is_crypto(position: dict[str, object]) -> bool:
    return normalized_type(position) == "crypto" or "crypto" in classified_text(position.get("sector")).casefold()


def is_equity(position: dict[str, object]) -> bool:
    asset_type = normalized_type(position)
    sector = classified_text(position.get("sector")).casefold()
    if asset_type == "stock":
        return True
    return asset_type == "etf" and any(term in sector for term in EQUITY_ETF_TERMS)


def is_technology(position: dict[str, object]) -> bool:
    sector = f" {classified_text(position.get('sector')).casefold()} "
    return any(term in sector for term in TECHNOLOGY_TERMS)


def broad_equity_shock(position: dict[str, object], largest_ticker: str) -> float | None:
    del largest_ticker
    return -0.20 if is_equity(position) else None


def technology_ai_shock(position: dict[str, object], largest_ticker: str) -> float | None:
    del largest_ticker
    if not is_equity(position):
        return None
    return -0.30 if is_technology(position) else -0.10


def crypto_shock(position: dict[str, object], largest_ticker: str) -> float | None:
    del largest_ticker
    return -0.40 if is_crypto(position) else None


def cad_strengthening_shock(position: dict[str, object], largest_ticker: str) -> float | None:
    del largest_ticker
    currency = classified_text(position.get("currency")).upper()
    return -0.10 if currency == "USD" else None


def concentration_shock(position: dict[str, object], largest_ticker: str) -> float | None:
    return -0.35 if text(position.get("ticker")).upper() == largest_ticker else None


SCENARIOS: tuple[dict[str, object], ...] = (
    {
        "scenario_id": "broad-equity-down-20",
        "name": "Broad equity -20%",
        "description": "Stocks and ETFs explicitly classified as equity decline 20%.",
        "shock": broad_equity_shock,
    },
    {
        "scenario_id": "technology-ai-down-30",
        "name": "Technology / AI -30%; other equity -10%",
        "description": "Technology and AI equity exposure declines 30%; other classified equity declines 10%.",
        "shock": technology_ai_shock,
    },
    {
        "scenario_id": "crypto-down-40",
        "name": "Crypto -40%",
        "description": "Positions explicitly classified as crypto decline 40%.",
        "shock": crypto_shock,
    },
    {
        "scenario_id": "cad-strengthens-10",
        "name": "CAD strengthens 10% against USD",
        "description": "Unhedged positions explicitly denominated in USD lose 10% in CAD-equivalent value using a linear first-order estimate.",
        "shock": cad_strengthening_shock,
    },
    {
        "scenario_id": "largest-position-down-35",
        "name": "Largest position -35%",
        "description": "The largest current position declines 35%; all other positions are unchanged.",
        "shock": concentration_shock,
    },
)


def scenario_as_of(portfolio_detail: dict[str, object]) -> str:
    explicit = text(portfolio_detail.get("as_of") or portfolio_detail.get("to_date"))
    if explicit:
        return explicit
    series = portfolio_detail.get("series")
    dates = [text(row.get("date")) for row in series if isinstance(row, dict) and row.get("date")] if isinstance(series, list) else []
    return max(dates, default=date.today().isoformat())


def scenario_response(portfolio_detail: dict[str, object], *, base_currency: str = "USD") -> dict[str, object]:
    raw_positions = portfolio_detail.get("positions")
    positions = [row for row in raw_positions if isinstance(row, dict)] if isinstance(raw_positions, list) else []
    warnings: list[str] = []
    usable: list[dict[str, object]] = []
    supplied_weight_total = 0.0
    supplied_weight_count = 0
    for index, position in enumerate(positions, start=1):
        ticker = text(position.get("ticker")).upper()
        value = float(position.get("current_value") or 0)
        if not ticker:
            warnings.append(f"position {index}: ticker is unavailable")
            continue
        if value <= 0:
            warnings.append(f"{ticker}: positive current value is unavailable")
            continue
        if position.get("weight_pct") is not None:
            supplied_weight_total += float(position.get("weight_pct") or 0)
            supplied_weight_count += 1
        missing = []
        if not normalized_type(position):
            missing.append("asset type")
        if not classified_text(position.get("sector")):
            missing.append("sector")
        if not classified_text(position.get("currency")):
            missing.append("currency")
        if missing:
            warnings.append(f"{ticker}: missing {', '.join(missing)}; affected scenarios remain unassigned")
        usable.append({**position, "ticker": ticker, "current_value": value})

    total_value = sum(float(position["current_value"]) for position in usable)
    largest = max(usable, key=lambda row: float(row["current_value"]), default=None)
    largest_ticker = text(largest.get("ticker")).upper() if largest else ""
    if supplied_weight_count and abs(supplied_weight_total - 100) > RECONCILIATION_TOLERANCE:
        warnings.append(
            f"Supplied position weights total {supplied_weight_total:.2f}%; scenario weights were normalized from current values."
        )
    elif not supplied_weight_count and usable:
        warnings.append("Position weights were not supplied; scenario weights were normalized from current values.")
    if not total_value:
        warnings.append("No positive current position values are available for scenario analysis.")

    results = []
    for scenario in SCENARIOS:
        shock_function = scenario["shock"]
        assert callable(shock_function)
        contributions = []
        for position in usable:
            shock = shock_function(position, largest_ticker)  # type: ignore[operator]
            if shock is None:
                continue
            dollar_impact = float(position["current_value"]) * float(shock)
            contributions.append(
                {
                    "ticker": position["ticker"],
                    "current_value": position["current_value"],
                    "portfolio_weight_pct": float(position["current_value"]) / total_value * 100 if total_value else 0.0,
                    "shock_pct": float(shock) * 100,
                    "estimated_dollar_impact": dollar_impact,
                    "portfolio_impact_pct": dollar_impact / total_value * 100 if total_value else 0.0,
                    "asset_type": normalized_type(position) or UNKNOWN,
                    "sector": text(position.get("sector")) or UNKNOWN,
                    "currency": text(position.get("currency")).upper() or UNKNOWN,
                }
            )
        dollar_impact = sum(float(row["estimated_dollar_impact"]) for row in contributions)
        impact_pct = dollar_impact / total_value * 100 if total_value else 0.0
        contribution_pct = sum(float(row["portfolio_impact_pct"]) for row in contributions)
        results.append(
            {
                "scenario_id": scenario["scenario_id"],
                "name": scenario["name"],
                "description": scenario["description"],
                "estimated_impact_pct": impact_pct,
                "estimated_dollar_impact": dollar_impact,
                "affected_position_count": len(contributions),
                "largest_affected_positions": sorted(
                    contributions,
                    key=lambda row: abs(float(row["estimated_dollar_impact"])),
                    reverse=True,
                )[:10],
                "reconciliation_difference_pct": impact_pct - contribution_pct,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "portfolio": text(portfolio_detail.get("investor") or portfolio_detail.get("portfolio_name")) or "Selected portfolio",
        "as_of": scenario_as_of(portfolio_detail),
        "base_currency": base_currency.upper(),
        "total_current_value": total_value,
        "position_count": len(usable),
        "scenarios": results,
        "assumptions": [
            "Results are deterministic linear first-order estimates, not forecasts.",
            "Position weights are normalized from positive current values.",
            "Unknown classifications remain unassigned rather than receiving an inferred shock.",
            "ETF constituent look-through, derivatives convexity, taxes, trading costs, and liquidity effects are excluded.",
            "The CAD scenario applies a linear -10% translation shock to positions explicitly marked USD.",
        ],
        "data_quality": {
            "warnings": warnings,
            "reconciliation_tolerance_pct": RECONCILIATION_TOLERANCE,
            "source_labels": ["supplied portfolio detail positions"],
            "write_behavior": "read_only_no_orders",
        },
    }
