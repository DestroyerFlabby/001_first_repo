from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.dashboard_cache import default_preload_window, preload_dashboard_cache  # noqa: E402


def preload_window(start: date, end: date, include_fx: bool, force: bool) -> None:
    for row in preload_dashboard_cache(start, end, include_fx=include_fx, force=force):
        print(
            f"Preloaded {row['kind']} {row['from_date']} to {row['to_date']} "
            f"| fx fees={row['wealthsimple_fx_fees']} | {row['cache_status']}"
        )
        print(f"  {row['path']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preload dashboard cache for the latest prior month-end through latest market close."
    )
    parser.add_argument("--from-date", help="Override the preload start date, YYYY-MM-DD.")
    parser.add_argument("--to-date", help="Override the preload end date, YYYY-MM-DD.")
    parser.add_argument("--include-fx", action="store_true", help="Also preload Wealthsimple FX-fee variants.")
    parser.add_argument("--force", action="store_true", help="Rebuild cached files even when they already exist.")
    args = parser.parse_args()

    configured_start = date.fromisoformat(args.from_date) if args.from_date else None
    configured_end = date.fromisoformat(args.to_date) if args.to_date else None
    start, end = default_preload_window(configured_start, configured_end)

    preload_window(start, end, include_fx=args.include_fx, force=args.force)
    print("Dashboard cache preload complete.")


if __name__ == "__main__":
    main()
