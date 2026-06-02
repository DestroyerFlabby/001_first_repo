from __future__ import annotations

import argparse
import time

from backend.dashboard_service import tracked_stock_assets
from backend.news_service import news_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh cached free-news snapshots for tracked stocks."
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        help="Optional ticker list. Defaults to every tracked stock.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between tickers to reduce public-source throttling.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    tickers = sorted(
        {ticker.upper() for ticker in args.tickers}
        or {ticker for ticker, _ in tracked_stock_assets()}
    )
    for index, ticker in enumerate(tickers, start=1):
        summary = news_summary(ticker)
        statuses = ", ".join(
            f"{row['source']}={row['status']}" for row in summary["sources"]
        )
        print(
            f"[{index}/{len(tickers)}] {ticker}: "
            f"24h={summary['articles_24h']} "
            f"7d={summary['articles_7d']} "
            f"velocity={summary['daily_velocity_ratio']} "
            f"({statuses})"
        )
        if index < len(tickers) and args.delay > 0:
            time.sleep(args.delay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
