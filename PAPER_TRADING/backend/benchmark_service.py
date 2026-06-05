from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_REGISTRY_FILE = ROOT / "data" / "benchmark_registry.csv"
BENCHMARK_COLUMNS = (
    "benchmark_id",
    "ticker",
    "name",
    "asset_type",
    "exchange",
    "currency",
    "category",
    "default_for",
    "active",
    "notes",
)


def parse_bool(value: str) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "on"}


def normalize_row(row: dict[str, str], row_number: int) -> dict[str, object]:
    benchmark_id = (row.get("benchmark_id") or "").strip().casefold()
    ticker = (row.get("ticker") or "").strip().upper()
    asset_type = (row.get("asset_type") or "").strip().lower()
    if not benchmark_id:
        raise ValueError(f"benchmark_registry.csv row {row_number}: benchmark_id is required")
    if not ticker:
        raise ValueError(f"benchmark_registry.csv row {row_number}: ticker is required")
    if not asset_type:
        raise ValueError(f"benchmark_registry.csv row {row_number}: asset_type is required")
    normalized: dict[str, object] = {
        column: (row.get(column) or "").strip()
        for column in BENCHMARK_COLUMNS
    }
    normalized["benchmark_id"] = benchmark_id
    normalized["ticker"] = ticker
    normalized["asset_type"] = asset_type
    normalized["active"] = parse_bool(str(normalized["active"]))
    return normalized


def read_benchmarks(include_inactive: bool = False) -> list[dict[str, object]]:
    if not BENCHMARK_REGISTRY_FILE.exists():
        return []
    with BENCHMARK_REGISTRY_FILE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != BENCHMARK_COLUMNS:
            raise ValueError("benchmark_registry.csv has unexpected columns")
        rows = [
            normalize_row(row, index)
            for index, row in enumerate(reader, start=2)
        ]
    seen: set[str] = set()
    for row in rows:
        benchmark_id = str(row["benchmark_id"])
        if benchmark_id in seen:
            raise ValueError(f"benchmark_registry.csv has duplicate benchmark_id: {benchmark_id}")
        seen.add(benchmark_id)
    if not include_inactive:
        rows = [row for row in rows if row["active"]]
    return sorted(rows, key=lambda row: str(row["benchmark_id"]))


def write_benchmarks(rows: list[dict[str, object]]) -> None:
    BENCHMARK_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with BENCHMARK_REGISTRY_FILE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BENCHMARK_COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in BENCHMARK_COLUMNS})


def benchmark_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().casefold()).strip("-")
    return slug or "custom-benchmark"


def upsert_benchmark(payload: dict[str, object]) -> dict[str, object]:
    ticker = str(payload.get("ticker") or "").strip().upper()
    benchmark_id = benchmark_slug(str(payload.get("benchmark_id") or ticker))
    row = normalize_row(
        {
            "benchmark_id": benchmark_id,
            "ticker": ticker,
            "name": str(payload.get("name") or ticker).strip(),
            "asset_type": str(payload.get("asset_type") or "etf").strip(),
            "exchange": str(payload.get("exchange") or "").strip(),
            "currency": str(payload.get("currency") or "USD").strip().upper(),
            "category": str(payload.get("category") or "").strip(),
            "default_for": str(payload.get("default_for") or "").strip(),
            "active": str(payload.get("active") if payload.get("active") is not None else "true"),
            "notes": str(payload.get("notes") or "").strip(),
        },
        0,
    )
    rows = read_benchmarks(include_inactive=True)
    by_id = {str(existing["benchmark_id"]): existing for existing in rows}
    by_id[str(row["benchmark_id"])] = row
    write_benchmarks(sorted(by_id.values(), key=lambda item: str(item["benchmark_id"])))
    return row


def benchmark_registry_response(include_inactive: bool = False) -> dict[str, object]:
    benchmarks = read_benchmarks(include_inactive=include_inactive)
    return {
        "benchmarks": benchmarks,
        "total": len(benchmarks),
        "include_inactive": include_inactive,
    }
