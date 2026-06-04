from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.dashboard_cache import cached_or_build_eod, cached_or_build_overview, cache_path  # noqa: E402
from backend.dashboard_service import fetch_chart  # noqa: E402


def latest_market_window() -> tuple[date, date]:
    _, bars = fetch_chart("SPY")
    if len(bars) < 2:
        raise ValueError("missing SPY market history")
    return bars[-2].day, bars[-1].day


def prior_month_end_market_date(latest: date) -> date:
    first_of_month = latest.replace(day=1)
    previous_month_calendar_end = first_of_month - timedelta(days=1)
    _, bars = fetch_chart("SPY")
    month_end = next(
        (bar.day for bar in reversed(bars) if bar.day <= previous_month_calendar_end),
        None,
    )
    if not month_end:
        raise ValueError("missing prior month-end market session")
    return month_end


def preload_window(start: date, end: date, include_fx: bool, force: bool) -> None:
    fee_options = [False, True] if include_fx else [False]
    for apply_fees in fee_options:
        print(f"Preloading overview {start.isoformat()} to {end.isoformat()} | fx fees={apply_fees}")
        cached_or_build_overview(start, end, apply_fees, force=force)
        print(f"  {cache_path('overview', start, end, apply_fees)}")

        previous, latest = latest_market_window()
        print(f"Preloading EOD {previous.isoformat()} to {latest.isoformat()} | fx fees={apply_fees}")
        cached_or_build_eod(apply_fees, force=force)
        print(f"  {cache_path('eod', previous, latest, apply_fees)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preload dashboard cache for the latest prior month-end through latest market close."
    )
    parser.add_argument("--from-date", help="Override the preload start date, YYYY-MM-DD.")
    parser.add_argument("--to-date", help="Override the preload end date, YYYY-MM-DD.")
    parser.add_argument("--include-fx", action="store_true", help="Also preload Wealthsimple FX-fee variants.")
    parser.add_argument("--force", action="store_true", help="Rebuild cached files even when they already exist.")
    args = parser.parse_args()

    _, latest = latest_market_window()
    start = date.fromisoformat(args.from_date) if args.from_date else prior_month_end_market_date(latest)
    end = date.fromisoformat(args.to_date) if args.to_date else latest
    if end < start:
        raise ValueError("--to-date must be on or after --from-date")

    preload_window(start, end, include_fx=args.include_fx, force=args.force)
    print("Dashboard cache preload complete.")


if __name__ == "__main__":
    main()
