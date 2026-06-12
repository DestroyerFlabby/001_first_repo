from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from backend.dashboard_service import (
    CRYPTO_SYMBOLS,
    TICKER_SECTOR_OVERRIDES,
    TSX_SYMBOLS,
    build_overview,
    trader_detail,
)
from backend.universe_service import read_asset_universe


SCHEMA_VERSION = "1.0"
CALCULATION_VERSION = "tracked-allocation-1.0"
UNKNOWN = "Unknown / Unclassified"


def decimal_value(value: object) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def normalized_key(ticker: object, asset_type: object) -> tuple[str, str]:
    return str(ticker or "").strip().upper(), str(asset_type or "").strip().casefold()


def metadata_index(rows: Iterable[dict[str, object]]) -> dict[tuple[str, str], dict[str, object]]:
    indexed: dict[tuple[str, str], dict[str, object]] = {}
    by_ticker: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = normalized_key(row.get("ticker"), row.get("asset_type"))
        if key[0] and key not in indexed:
            indexed[key] = row
            by_ticker[key[0]].append(row)
    for ticker, ticker_rows in by_ticker.items():
        if len(ticker_rows) == 1:
            indexed[(ticker, "")] = ticker_rows[0]
    return indexed


def resolved_instrument_metadata(
    ticker: str,
    asset_type: str,
    position: dict[str, object],
    meta: dict[str, object],
) -> dict[str, str]:
    resolved_type = asset_type or str(meta.get("asset_type") or "").strip().casefold()
    if not resolved_type and ticker in CRYPTO_SYMBOLS:
        resolved_type = "crypto"

    sector = str(position.get("sector") or meta.get("sector") or "").strip()
    if not sector or sector.casefold() == "unclassified":
        sector = TICKER_SECTOR_OVERRIDES.get(ticker, "")
    if not sector and resolved_type == "crypto":
        sector = "Crypto"
    if not sector and resolved_type == "etf":
        sector = "ETF / Other"

    currency = str(position.get("currency") or meta.get("currency") or "").strip().upper()
    exchange = str(meta.get("exchange") or "").strip().upper()
    if not currency and ticker in TSX_SYMBOLS:
        currency = "CAD"
    if not currency and resolved_type == "crypto" and ticker in CRYPTO_SYMBOLS:
        currency = "USD"
    if not currency and resolved_type in {"stock", "etf"}:
        if exchange in {"TSX", "TSXV", "TSX-V", "NEO", "CSE"}:
            currency = "CAD"
        elif ticker and ticker not in TSX_SYMBOLS:
            currency = "USD"

    return {
        "asset_type": resolved_type or UNKNOWN,
        "sector": sector or UNKNOWN,
        "currency": currency or UNKNOWN,
    }


def allocation_rows(values: dict[str, Decimal], total: Decimal) -> list[dict[str, object]]:
    rows = [
        {
            "name": name,
            "current_value": float(value),
            "weight_pct": float(value / total * 100) if total else 0.0,
        }
        for name, value in values.items()
        if value > 0
    ]
    return sorted(rows, key=lambda row: (-float(row["current_value"]), str(row["name"])))


def concentration_alerts(
    portfolio_rows: list[dict[str, object]],
    security_rows: list[dict[str, object]],
    sector_rows: list[dict[str, object]],
    currency_rows: list[dict[str, object]],
    metadata_coverage_pct: float,
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    top_security = security_rows[0] if security_rows else None
    top_portfolio = portfolio_rows[0] if portfolio_rows else None
    top_sector = sector_rows[0] if sector_rows else None
    top_currency = currency_rows[0] if currency_rows else None
    if top_security and float(top_security["weight_pct"]) > 10:
        alerts.append(
            {
                "severity": "high",
                "code": "single_security_concentration",
                "message": f"{top_security['ticker']} represents {top_security['weight_pct']:.1f}% of tracked value.",
                "decision": "Review position sizing and overlap across tracked portfolios.",
            }
        )
    if top_portfolio and float(top_portfolio["weight_pct"]) > 25:
        alerts.append(
            {
                "severity": "medium",
                "code": "portfolio_concentration",
                "message": f"{top_portfolio['name']} represents {top_portfolio['weight_pct']:.1f}% of tracked value.",
                "decision": "Confirm that comparisons are not dominated by one strategy's capital base.",
            }
        )
    if top_sector and top_sector["name"] != UNKNOWN and float(top_sector["weight_pct"]) > 35:
        alerts.append(
            {
                "severity": "high",
                "code": "sector_concentration",
                "message": f"{top_sector['name']} represents {top_sector['weight_pct']:.1f}% of tracked value.",
                "decision": "Review cross-portfolio sector overlap before adding similar exposure.",
            }
        )
    if top_currency and top_currency["name"] != UNKNOWN and float(top_currency["weight_pct"]) > 80:
        alerts.append(
            {
                "severity": "medium",
                "code": "currency_concentration",
                "message": f"{top_currency['name']} represents {top_currency['weight_pct']:.1f}% of tracked value.",
                "decision": "Evaluate whether the currency exposure matches the intended base-currency policy.",
            }
        )
    if metadata_coverage_pct < 95:
        alerts.append(
            {
                "severity": "data_quality",
                "code": "metadata_coverage",
                "message": f"Complete classification metadata covers {metadata_coverage_pct:.1f}% of tracked value.",
                "decision": "Resolve unknown classifications before relying on allocation limits.",
            }
        )
    return alerts


def build_allocation_response(
    portfolios: Iterable[dict[str, object]],
    metadata_rows: Iterable[dict[str, object]],
    *,
    as_of: date,
    start: date | None = None,
    base_currency: str = "USD",
    source_labels: Iterable[str] = ("dashboard_service", "asset_universe.csv"),
) -> dict[str, object]:
    metadata = metadata_index(metadata_rows)
    unique_portfolios: dict[str, dict[str, object]] = {}
    duplicate_names: list[str] = []
    for portfolio in portfolios:
        name = str(portfolio.get("investor") or portfolio.get("portfolio_name") or "").strip()
        key = name.casefold()
        if not key:
            continue
        if key in unique_portfolios:
            duplicate_names.append(name)
            continue
        unique_portfolios[key] = portfolio

    portfolio_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    sector_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    type_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    currency_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    security_values: defaultdict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    security_metadata: dict[tuple[str, str], dict[str, str]] = {}
    warnings: list[str] = []
    classified_value = Decimal("0")
    type_classified_value = Decimal("0")
    sector_classified_value = Decimal("0")
    currency_classified_value = Decimal("0")
    position_rows = 0

    for portfolio in unique_portfolios.values():
        portfolio_name = str(portfolio.get("investor") or portfolio.get("portfolio_name"))
        positions = portfolio.get("positions")
        if not isinstance(positions, list):
            warnings.append(f"{portfolio_name}: positions are unavailable")
            continue
        for position in positions:
            if not isinstance(position, dict):
                continue
            value = decimal_value(position.get("current_value"))
            if value <= 0:
                continue
            ticker, asset_type = normalized_key(
                position.get("ticker"),
                position.get("security_type") or position.get("asset_type"),
            )
            if not ticker:
                warnings.append(f"{portfolio_name}: ignored a position without a ticker")
                continue
            meta = metadata.get((ticker, asset_type)) or metadata.get((ticker, "")) or {}
            resolved = resolved_instrument_metadata(ticker, asset_type, position, meta)
            resolved_type = resolved["asset_type"]
            sector = resolved["sector"]
            currency = resolved["currency"]
            complete = resolved_type != UNKNOWN and sector != UNKNOWN and currency != UNKNOWN
            if complete:
                classified_value += value
            if resolved_type != UNKNOWN:
                type_classified_value += value
            if sector != UNKNOWN:
                sector_classified_value += value
            if currency != UNKNOWN:
                currency_classified_value += value
            portfolio_values[portfolio_name] += value
            sector_values[sector] += value
            type_values[resolved_type] += value
            currency_values[currency] += value
            security_values[(ticker, resolved_type)] += value
            security_metadata[(ticker, resolved_type)] = {
                "ticker": ticker,
                "asset_type": resolved_type,
                "sector": sector,
                "currency": currency,
            }
            position_rows += 1

    total = sum(portfolio_values.values(), Decimal("0"))
    portfolio_rows = allocation_rows(dict(portfolio_values), total)
    sector_rows = allocation_rows(dict(sector_values), total)
    type_rows = allocation_rows(dict(type_values), total)
    currency_rows = allocation_rows(dict(currency_values), total)
    security_rows = []
    for key, value in security_values.items():
        row = security_metadata[key]
        security_rows.append(
            {
                **row,
                "current_value": float(value),
                "weight_pct": float(value / total * 100) if total else 0.0,
            }
        )
    security_rows.sort(key=lambda row: (-float(row["current_value"]), str(row["ticker"])))

    weights = [decimal_value(row["weight_pct"]) / Decimal("100") for row in security_rows]
    herfindahl = sum((weight * weight for weight in weights), Decimal("0"))
    top_weight = float(security_rows[0]["weight_pct"]) if security_rows else 0.0
    top_five = sum((float(row["weight_pct"]) for row in security_rows[:5]), 0.0)
    effective_holdings = float(Decimal("1") / herfindahl) if herfindahl else 0.0
    coverage_pct = float(classified_value / total * 100) if total else 0.0
    type_coverage_pct = float(type_classified_value / total * 100) if total else 0.0
    sector_coverage_pct = float(sector_classified_value / total * 100) if total else 0.0
    currency_coverage_pct = float(currency_classified_value / total * 100) if total else 0.0
    alerts = concentration_alerts(portfolio_rows, security_rows, sector_rows, currency_rows, coverage_pct)
    if duplicate_names:
        warnings.append(f"Ignored duplicate portfolio records: {', '.join(sorted(set(duplicate_names)))}")
    if not total:
        warnings.append("No positive current position values were available for allocation analysis.")

    return {
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "as_of": as_of.isoformat(),
        "from_date": start.isoformat() if start else None,
        "base_currency": base_currency,
        "view_type": "tracked_portfolio_research_collection",
        "view_note": "Values aggregate unique tracked portfolio simulations and are not a consolidated household balance sheet.",
        "total_current_value": float(total),
        "included_portfolio_count": len(portfolio_rows),
        "position_record_count": position_rows,
        "unique_security_count": len(security_rows),
        "allocation": {
            "portfolio_strategy": portfolio_rows,
            "sector": sector_rows,
            "asset_type": type_rows,
            "currency": currency_rows,
            "security": security_rows,
        },
        "concentration": {
            "top_position_weight_pct": top_weight,
            "top_five_weight_pct": top_five,
            "effective_number_of_holdings": effective_holdings,
        },
        "metadata_coverage": {
            "complete_value_pct": coverage_pct,
            "asset_type_value_pct": type_coverage_pct,
            "sector_value_pct": sector_coverage_pct,
            "currency_value_pct": currency_coverage_pct,
            "unknown_sector_value": float(sector_values.get(UNKNOWN, Decimal("0"))),
            "unknown_asset_type_value": float(type_values.get(UNKNOWN, Decimal("0"))),
            "unknown_currency_value": float(currency_values.get(UNKNOWN, Decimal("0"))),
        },
        "concentration_alerts": alerts,
        "data_quality": {
            "freshness": {"as_of": as_of.isoformat(), "status": "selected_window_close"},
            "completeness_pct": coverage_pct,
            "warnings": warnings,
            "assumptions": [
                "Only unique primary tracked portfolios with positive current position values are included.",
                "Portfolio simulations are summed as a research collection; shared securities are intentionally combined to reveal overlap.",
                "Values are treated as already normalized to the dashboard reporting currency.",
                "Unknown classifications remain visible and are never redistributed.",
            ],
            "source_labels": list(source_labels),
        },
    }


def wealth_allocation_response(
    start: date,
    end: date,
    apply_wealthsimple_fx_fees: bool = False,
    overview_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    overview = overview_payload or build_overview(start, end, apply_wealthsimple_fx_fees)
    primary = [
        row
        for row in overview.get("traders", [])
        if isinstance(row, dict) and row.get("portfolio_group") == "primary"
    ]
    details: list[dict[str, Any]] = []
    failures: list[str] = []
    seen: set[str] = set()
    for summary in primary:
        name = str(summary.get("investor") or "").strip()
        key = name.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            details.append(trader_detail(name, start, end, apply_wealthsimple_fx_fees))
        except (KeyError, ValueError) as exc:
            failures.append(f"{name}: {exc}")
    response = build_allocation_response(
        details,
        read_asset_universe(),
        as_of=end,
        start=start,
        base_currency="USD",
    )
    response["data_quality"]["warnings"].extend(failures)  # type: ignore[index]
    return response
