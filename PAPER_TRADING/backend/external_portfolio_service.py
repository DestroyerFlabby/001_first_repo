from __future__ import annotations

import csv
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_FILE = ROOT / "data" / "external_portfolio_registry.csv"
TRADES_FILE = ROOT / "data" / "trades.csv"
REGISTRY_FIELDS = [
    "portfolio_id",
    "portfolio_name",
    "portfolio_type",
    "status",
    "source_system",
    "source_path",
    "benchmark",
    "inception_date",
    "execution_convention",
    "notes",
]
SNAPSHOT_FIELDS = [
    "snapshot_date",
    "ticker",
    "asset_type",
    "target_weight",
    "signal_date",
    "source",
    "confidence",
    "thesis",
    "status",
]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def decimal_or_none(value: object) -> Decimal | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def validate_snapshot(path: Path) -> dict[str, Any]:
    fields, raw_rows = read_csv(path)
    errors: list[str] = []
    warnings: list[str] = []
    if fields != SNAPSHOT_FIELDS:
        errors.append(f"expected columns: {', '.join(SNAPSHOT_FIELDS)}")
        return {"rows": [], "errors": errors, "warnings": warnings}

    rows: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows, start=2):
        ticker = str(row.get("ticker") or "").strip().upper()
        snapshot_date = str(row.get("snapshot_date") or "").strip()
        asset_type = str(row.get("asset_type") or "").strip().casefold()
        weight = decimal_or_none(row.get("target_weight"))
        if not ticker:
            errors.append(f"row {index}: ticker is required")
        if snapshot_date:
            try:
                date.fromisoformat(snapshot_date)
            except ValueError:
                errors.append(f"row {index}: snapshot_date must use YYYY-MM-DD")
        else:
            errors.append(f"row {index}: snapshot_date is required")
        if asset_type not in {"stock", "etf", "crypto"}:
            errors.append(f"row {index}: invalid asset_type '{asset_type}'")
        if weight is None or weight < 0:
            errors.append(f"row {index}: target_weight must be non-negative")
        rows.append({**row, "ticker": ticker, "asset_type": asset_type, "target_weight": float(weight or 0)})

    dates = sorted({str(row.get("snapshot_date") or "") for row in rows if row.get("snapshot_date")})
    latest_date = dates[-1] if dates else None
    latest_rows = [row for row in rows if row.get("snapshot_date") == latest_date]
    latest_weight = sum(Decimal(str(row["target_weight"])) for row in latest_rows)
    if latest_rows and abs(latest_weight - Decimal("100")) > Decimal("0.01"):
        warnings.append(f"latest snapshot weights total {latest_weight}% instead of 100%")
    duplicates = [
        ticker
        for ticker, count in Counter(str(row["ticker"]) for row in latest_rows).items()
        if count > 1
    ]
    if duplicates:
        errors.append(f"latest snapshot has duplicate tickers: {', '.join(sorted(duplicates))}")
    return {
        "rows": rows,
        "latest_rows": latest_rows,
        "latest_snapshot_date": latest_date,
        "latest_weight_pct": float(latest_weight),
        "errors": errors,
        "warnings": warnings,
    }


def social_ledger_status() -> dict[str, Any]:
    fields, rows = read_csv(TRADES_FILE)
    if "investor" not in fields:
        return {"position_count": 0, "latest_activity_date": None, "errors": ["trades.csv missing investor column"]}
    matched = [row for row in rows if str(row.get("investor") or "").casefold() == "insta_watchlist"]
    tickers = sorted({str(row.get("ticker") or "").upper() for row in matched if row.get("ticker")})
    activity_dates = sorted(str(row.get("timestamp") or "")[:10] for row in matched if row.get("timestamp"))
    return {
        "position_count": len(tickers),
        "tickers": tickers,
        "latest_activity_date": activity_dates[-1] if activity_dates else None,
        "errors": [],
    }


def external_portfolio_response() -> dict[str, Any]:
    fields, registry_rows = read_csv(REGISTRY_FILE)
    if fields != REGISTRY_FIELDS:
        raise ValueError("external_portfolio_registry.csv has unexpected columns")
    portfolios = []
    for raw in registry_rows:
        row = {field: str(raw.get(field) or "").strip() for field in REGISTRY_FIELDS}
        portfolio_id = row["portfolio_id"].casefold()
        source_path = ROOT / row["source_path"]
        if portfolio_id == "social-media-signal" and row["source_system"] == "paper-trading-ledger":
            source_status = social_ledger_status()
            source_status.update({"latest_weight_pct": None, "warnings": []})
        else:
            source_status = validate_snapshot(source_path)
            source_status["position_count"] = len(source_status.get("latest_rows", []))
            source_status.pop("rows", None)
            source_status.pop("latest_rows", None)
        effective_status = row["status"]
        if source_status.get("errors"):
            effective_status = "invalid_source"
        elif not source_status.get("position_count"):
            effective_status = "awaiting_source"
        portfolios.append(
            {
                **row,
                "portfolio_id": portfolio_id,
                "effective_status": effective_status,
                "source_status": source_status,
            }
        )
    return {
        "portfolios": portfolios,
        "summary": {
            "portfolio_count": len(portfolios),
            "active_count": sum(row["effective_status"] == "active" for row in portfolios),
            "awaiting_source_count": sum(row["effective_status"] == "awaiting_source" for row in portfolios),
            "invalid_source_count": sum(row["effective_status"] == "invalid_source" for row in portfolios),
        },
        "snapshot_contract": SNAPSHOT_FIELDS,
        "note": "External portfolio files are tracking inputs only. They do not create broker orders.",
    }
