from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from backend.dashboard_service import build_eod_snapshot, build_overview, fetch_chart


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "dashboard_cache"
CACHE_VERSION = 1


def cache_token(value: object) -> str:
    return str(value).replace("/", "-").replace("\\", "-").replace(":", "-")


def cache_path(kind: str, start: date | None, end: date | None, apply_fees: bool) -> Path:
    start_part = cache_token(start.isoformat() if start else "auto")
    end_part = cache_token(end.isoformat() if end else "latest")
    fee_part = "fx1" if apply_fees else "fx0"
    return CACHE_DIR / f"{kind}__{start_part}__{end_part}__{fee_part}.json"


def read_cache(kind: str, start: date | None, end: date | None, apply_fees: bool) -> dict[str, Any] | None:
    path = cache_path(kind, start, end, apply_fees)
    if not path.exists():
        return None
    try:
        wrapped = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    metadata = wrapped.get("cache") if isinstance(wrapped, dict) else None
    payload = wrapped.get("payload") if isinstance(wrapped, dict) else None
    if not isinstance(metadata, dict) or not isinstance(payload, dict):
        return None
    if metadata.get("version") != CACHE_VERSION or metadata.get("kind") != kind:
        return None
    return {**payload, "cache_status": "hit", "cache_created_at": metadata.get("created_at")}


def write_cache(
    kind: str,
    start: date | None,
    end: date | None,
    apply_fees: bool,
    payload: dict[str, Any],
) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = cache_path(kind, start, end, apply_fees)
    wrapped = {
        "cache": {
            "version": CACHE_VERSION,
            "kind": kind,
            "from_date": start.isoformat() if start else None,
            "to_date": end.isoformat() if end else None,
            "wealthsimple_fx_fees": apply_fees,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "payload": payload,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(wrapped, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
    return path


def cached_or_build(
    kind: str,
    start: date | None,
    end: date | None,
    apply_fees: bool,
    builder: Callable[[], dict[str, Any]],
    force: bool = False,
) -> dict[str, Any]:
    if not force:
        cached = read_cache(kind, start, end, apply_fees)
        if cached is not None:
            return cached
    payload = builder()
    write_cache(kind, start, end, apply_fees, payload)
    return {**payload, "cache_status": "miss"}


def cached_or_build_overview(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    if end is None:
        return build_overview(start, end, apply_wealthsimple_fx_fees)
    return cached_or_build(
        "overview",
        start,
        end,
        apply_wealthsimple_fx_fees,
        lambda: build_overview(start, end, apply_wealthsimple_fx_fees),
        force=force,
    )


def latest_eod_window() -> tuple[date, date]:
    _, market_bars = fetch_chart("SPY")
    if len(market_bars) < 2:
        raise ValueError("missing market sessions for EOD snapshot")
    return market_bars[-2].day, market_bars[-1].day


def cached_or_build_eod(
    apply_wealthsimple_fx_fees: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    previous, latest = latest_eod_window()
    return cached_or_build(
        "eod",
        previous,
        latest,
        apply_wealthsimple_fx_fees,
        lambda: build_eod_snapshot(apply_wealthsimple_fx_fees),
        force=force,
    )
