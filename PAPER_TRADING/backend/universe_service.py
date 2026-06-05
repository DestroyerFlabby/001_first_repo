from __future__ import annotations

import csv
from collections import Counter
from datetime import date
from pathlib import Path
from threading import Lock


ROOT = Path(__file__).resolve().parents[1]
ASSET_UNIVERSE_FILE = ROOT / "data" / "asset_universe.csv"
ASSET_UNIVERSE_EVENT_FILE = ROOT / "data" / "asset_universe_events.csv"
WRITE_LOCK = Lock()
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
ASSET_UNIVERSE_EVENT_COLUMNS = (
    "event_date",
    "ticker",
    "asset_type",
    "action",
    "previous_status",
    "new_status",
    "source",
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
WRITABLE_FIELDS = {
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
    "archived_at",
    "notes",
}


def parse_bool(value: str) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "on"}


def bool_text(value: object) -> str:
    return "true" if parse_bool(str(value)) else "false"


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


def serialize_row(row: dict[str, object]) -> dict[str, str]:
    output = {
        column: str(row.get(column, "") or "")
        for column in ASSET_UNIVERSE_COLUMNS
    }
    output["ticker"] = output["ticker"].strip().upper()
    output["asset_type"] = output["asset_type"].strip().lower()
    output["status"] = output["status"].strip().lower()
    for field in BOOLEAN_FIELDS:
        output[field] = bool_text(output[field])
    return output


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


def write_asset_universe(rows: list[dict[str, object]]) -> None:
    serialized = [serialize_row(row) for row in rows]
    normalized = [
        normalize_row(row, index)
        for index, row in enumerate(serialized, start=2)
    ]
    seen: set[tuple[str, str]] = set()
    for row in normalized:
        key = (str(row["ticker"]), str(row["asset_type"]))
        if key in seen:
            raise ValueError(f"asset_universe.csv has duplicate asset: {key[0]} {key[1]}")
        seen.add(key)
    serialized = [
        serialize_row(row)
        for row in sorted(normalized, key=lambda item: (str(item["ticker"]), str(item["asset_type"])))
    ]
    ASSET_UNIVERSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ASSET_UNIVERSE_FILE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ASSET_UNIVERSE_COLUMNS)
        writer.writeheader()
        writer.writerows(serialized)


def read_asset_events(limit: int = 50) -> list[dict[str, str]]:
    if not ASSET_UNIVERSE_EVENT_FILE.exists():
        return []
    with ASSET_UNIVERSE_EVENT_FILE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != ASSET_UNIVERSE_EVENT_COLUMNS:
            raise ValueError("asset_universe_events.csv has unexpected columns")
        rows = list(reader)
    return list(reversed(rows[-limit:]))


def append_asset_event(
    ticker: str,
    asset_type: str,
    action: str,
    previous: dict[str, object] | None,
    current: dict[str, object],
) -> None:
    ASSET_UNIVERSE_EVENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    exists = ASSET_UNIVERSE_EVENT_FILE.exists()
    with ASSET_UNIVERSE_EVENT_FILE.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ASSET_UNIVERSE_EVENT_COLUMNS, quoting=csv.QUOTE_ALL)
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "event_date": date.today().isoformat(),
                "ticker": ticker,
                "asset_type": asset_type,
                "action": action,
                "previous_status": "" if previous is None else previous.get("status", ""),
                "new_status": current.get("status", ""),
                "source": current.get("source", ""),
                "notes": current.get("notes", ""),
            }
        )


def resolve_asset(
    rows: list[dict[str, object]],
    ticker: str,
    asset_type: str | None = None,
) -> tuple[int, dict[str, object]]:
    normalized_ticker = ticker.strip().upper()
    matches = [
        (index, row)
        for index, row in enumerate(rows)
        if row["ticker"] == normalized_ticker
        and (asset_type is None or row["asset_type"] == asset_type.strip().lower())
    ]
    if not matches:
        raise KeyError(normalized_ticker)
    if len(matches) > 1:
        raise ValueError("asset_type is required when a ticker has multiple asset types")
    return matches[0]


def apply_updates(row: dict[str, object], updates: dict[str, object]) -> dict[str, object]:
    next_row = {**row}
    for field, value in updates.items():
        if field not in WRITABLE_FIELDS:
            continue
        if field in BOOLEAN_FIELDS:
            next_row[field] = parse_bool(str(value))
        elif field == "status":
            status = str(value).strip().lower()
            if status not in ALLOWED_STATUSES:
                raise ValueError(f"invalid status: {status}")
            next_row[field] = status
            if status == "archived" and not next_row.get("archived_at"):
                next_row["archived_at"] = date.today().isoformat()
            elif status != "archived" and updates.get("archived_at") is None:
                next_row["archived_at"] = ""
        else:
            next_row[field] = str(value or "").strip()
    return next_row


def upsert_asset(payload: dict[str, object]) -> dict[str, object]:
    ticker = str(payload.get("ticker") or "").strip().upper()
    asset_type = str(payload.get("asset_type") or "").strip().lower()
    if not ticker:
        raise ValueError("ticker is required")
    if not asset_type:
        raise ValueError("asset_type is required")
    with WRITE_LOCK:
        rows = read_asset_universe()
        existing: dict[str, object] | None = None
        action = "add"
        try:
            index, existing = resolve_asset(rows, ticker, asset_type)
            rows[index] = apply_updates(existing, payload)
            action = "status_change" if rows[index].get("status") != existing.get("status") else "update"
        except KeyError:
            status = str(payload.get("status") or "candidate").strip().lower()
            if status not in ALLOWED_STATUSES:
                raise ValueError(f"invalid status: {status}")
            row: dict[str, object] = {
                "ticker": ticker,
                "asset_type": asset_type,
                "exchange": "",
                "currency": "",
                "sector": "",
                "theme": "",
                "source": "manual-ui",
                "status": status,
                "strategy_eligible": False,
                "watchlist_eligible": True,
                "benchmark_eligible": False,
                "wealthsimple_supported_status": "unknown",
                "added_at": date.today().isoformat(),
                "archived_at": "",
                "notes": "",
            }
            rows.append(apply_updates(row, payload))
        write_asset_universe(rows)
        _, saved = resolve_asset(read_asset_universe(), ticker, asset_type)
        append_asset_event(ticker, asset_type, action, existing, saved)
        return saved


def update_asset(
    ticker: str,
    payload: dict[str, object],
    asset_type: str | None = None,
) -> dict[str, object]:
    with WRITE_LOCK:
        rows = read_asset_universe()
        index, existing = resolve_asset(rows, ticker, asset_type)
        rows[index] = apply_updates(existing, payload)
        action = "status_change" if rows[index].get("status") != existing.get("status") else "update"
        write_asset_universe(rows)
        _, saved = resolve_asset(read_asset_universe(), ticker, asset_type or str(existing["asset_type"]))
        append_asset_event(str(saved["ticker"]), str(saved["asset_type"]), action, existing, saved)
        return saved


def asset_universe_response() -> dict[str, object]:
    assets = read_asset_universe()
    status_counts = Counter(str(row["status"]) for row in assets)
    type_counts = Counter(str(row["asset_type"]) for row in assets)
    return {
        "assets": assets,
        "statuses": sorted(ALLOWED_STATUSES),
        "status_counts": dict(sorted(status_counts.items())),
        "asset_type_counts": dict(sorted(type_counts.items())),
        "recent_events": read_asset_events(),
        "total": len(assets),
    }
