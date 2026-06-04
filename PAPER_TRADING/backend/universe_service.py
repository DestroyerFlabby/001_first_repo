from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_UNIVERSE_FILE = ROOT / "data" / "asset_universe.csv"
ASSET_UNIVERSE_COLUMNS = (
    "ticker",
    "asset_type",
    "exchange",
    "currency",
    "sector",
    "theme",
    "source",
    "status",
    "strategy_eligible",
    "watchlist_eligible",
    "benchmark_eligible",
    "wealthsimple_supported_status",
    "added_at",
    "archived_at",
    "notes",
)
ALLOWED_STATUSES = {
    "active",
    "watch_only",
    "candidate",
    "strategy_eligible",
    "archived",
    "excluded",
    "benchmark",
}
BOOLEAN_FIELDS = {
    "strategy_eligible",
    "watchlist_eligible",
    "benchmark_eligible",
}


def parse_bool(value: str) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "on"}


def normalize_row(row: dict[str, str], row_number: int) -> dict[str, object]:
    ticker = (row.get("ticker") or "").strip().upper()
    asset_type = (row.get("asset_type") or "").strip().lower()
    status = (row.get("status") or "").strip().lower()
    if not ticker:
        raise ValueError(f"asset_universe.csv row {row_number}: ticker is required")
    if not asset_type:
        raise ValueError(f"asset_universe.csv row {row_number}: asset_type is required")
    if status not in ALLOWED_STATUSES:
        raise ValueError(
            f"asset_universe.csv row {row_number}: invalid status '{status}'"
        )

    normalized: dict[str, object] = {
        column: (row.get(column) or "").strip()
        for column in ASSET_UNIVERSE_COLUMNS
    }
    normalized["ticker"] = ticker
    normalized["asset_type"] = asset_type
    normalized["status"] = status
    for field in BOOLEAN_FIELDS:
        normalized[field] = parse_bool(str(normalized[field]))
    return normalized


def read_asset_universe() -> list[dict[str, object]]:
    if not ASSET_UNIVERSE_FILE.exists():
        return []
    with ASSET_UNIVERSE_FILE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != ASSET_UNIVERSE_COLUMNS:
            raise ValueError("asset_universe.csv has unexpected columns")
        rows = [
            normalize_row(row, index)
            for index, row in enumerate(reader, start=2)
        ]
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row["ticker"]), str(row["asset_type"]))
        if key in seen:
            raise ValueError(f"asset_universe.csv has duplicate asset: {key[0]} {key[1]}")
        seen.add(key)
    return sorted(rows, key=lambda row: (str(row["ticker"]), str(row["asset_type"])))


def asset_universe_response() -> dict[str, object]:
    assets = read_asset_universe()
    status_counts = Counter(str(row["status"]) for row in assets)
    type_counts = Counter(str(row["asset_type"]) for row in assets)
    return {
        "assets": assets,
        "statuses": sorted(ALLOWED_STATUSES),
        "status_counts": dict(sorted(status_counts.items())),
        "asset_type_counts": dict(sorted(type_counts.items())),
        "total": len(assets),
    }
