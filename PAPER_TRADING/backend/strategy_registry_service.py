from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STRATEGY_REGISTRY_FILE = ROOT / "data" / "strategy_registry.csv"
STRATEGY_FIELDS = [
    "strategy_id",
    "strategy_name",
    "status",
    "created_at",
    "forward_test_start_date",
    "entry_rule",
    "exit_rule",
    "news_rule",
    "universe",
    "benchmark",
    "position_size",
    "notes",
]
VALID_STATUSES = {"research", "backtested", "forward_testing", "active", "retired"}


def normalize_strategy(row: dict[str, str], row_number: int) -> dict[str, object]:
    normalized = {field: (row.get(field) or "").strip() for field in STRATEGY_FIELDS}
    strategy_id = normalized["strategy_id"].casefold()
    status = normalized["status"].casefold()
    if not strategy_id:
        raise ValueError(f"strategy_registry.csv row {row_number}: strategy_id is required")
    if not normalized["strategy_name"]:
        raise ValueError(f"strategy_registry.csv row {row_number}: strategy_name is required")
    if status not in VALID_STATUSES:
        raise ValueError(f"strategy_registry.csv row {row_number}: invalid status '{status}'")
    normalized["strategy_id"] = strategy_id
    normalized["status"] = status
    return normalized


def read_strategies(include_retired: bool = False) -> list[dict[str, object]]:
    if not STRATEGY_REGISTRY_FILE.exists():
        return []
    with STRATEGY_REGISTRY_FILE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != STRATEGY_FIELDS:
            raise ValueError("strategy_registry.csv has unexpected columns")
        rows = [
            normalize_strategy(row, index)
            for index, row in enumerate(reader, start=2)
        ]
    seen: set[str] = set()
    filtered: list[dict[str, object]] = []
    for row in rows:
        strategy_id = str(row["strategy_id"])
        if strategy_id in seen:
            raise ValueError(f"strategy_registry.csv has duplicate strategy_id: {strategy_id}")
        seen.add(strategy_id)
        if row["status"] == "retired" and not include_retired:
            continue
        filtered.append(row)
    return sorted(filtered, key=lambda row: (str(row["status"]), str(row["strategy_id"])))


def strategy_registry_response(include_retired: bool = False) -> dict[str, object]:
    strategies = read_strategies(include_retired=include_retired)
    status_counts = {
        status: sum(row["status"] == status for row in strategies)
        for status in sorted(VALID_STATUSES)
    }
    return {
        "strategies": strategies,
        "total": len(strategies),
        "status_counts": status_counts,
        "statuses": sorted(VALID_STATUSES),
    }
