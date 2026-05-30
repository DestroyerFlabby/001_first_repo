from __future__ import annotations

import argparse
import calendar
import json
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ENV_FILE = Path(__file__).parent.parent / ".env"


def load_dotenv() -> None:
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def eastern_timezone(day: date) -> timezone:
    march = calendar.monthcalendar(day.year, 3)
    november = calendar.monthcalendar(day.year, 11)
    dst_start = next(week[calendar.SUNDAY] for week in march if week[calendar.SUNDAY]) + 7
    dst_end = next(week[calendar.SUNDAY] for week in november if week[calendar.SUNDAY])
    is_dst = (day.month, day.day) >= (3, dst_start) and (day.month, day.day) < (
        11,
        dst_end,
    )
    return timezone(timedelta(hours=-4 if is_dst else -5))


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use an ISO-8601 date or timestamp") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=eastern_timezone(parsed.date()))
    return parsed


def fetch_bar(ticker: str, timestamp: datetime, basis: str) -> dict[str, object]:
    load_dotenv()
    api_key = os.environ.get("ALPACA_KEY") or os.environ.get("APCA_API_KEY_ID")
    api_secret = os.environ.get("ALPACA_SECRET") or os.environ.get("APCA_API_SECRET_KEY")
    if not api_key or not api_secret:
        raise RuntimeError("set ALPACA_KEY and ALPACA_SECRET in the repo .env file first")

    local_timestamp = timestamp.astimezone(eastern_timezone(timestamp.date()))
    if basis == "intraday":
        start = local_timestamp.replace(second=0, microsecond=0)
        end = start + timedelta(minutes=1)
        timeframe = "1Min"
    else:
        start = datetime.combine(
            local_timestamp.date(),
            time.min,
            tzinfo=eastern_timezone(local_timestamp.date()),
        )
        end = start + timedelta(days=1)
        timeframe = "1Day"

    query = urlencode(
        {
            "timeframe": timeframe,
            "start": start.astimezone(timezone.utc).isoformat(),
            "end": end.astimezone(timezone.utc).isoformat(),
            "feed": "iex",
            "adjustment": "raw",
            "limit": 10,
            "sort": "asc",
        }
    )
    url = f"https://data.alpaca.markets/v2/stocks/{ticker}/bars?{query}"
    request = Request(
        url,
        headers={
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
        },
    )
    with urlopen(request, timeout=15) as response:
        payload = json.load(response)
    bars = payload.get("bars", [])
    if not bars:
        raise RuntimeError("no bar returned; check the timestamp and market hours")
    return bars[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Look up an estimated stock price using Alpaca's free IEX feed."
    )
    parser.add_argument("ticker")
    parser.add_argument("timestamp", type=parse_timestamp)
    parser.add_argument("--basis", choices=["intraday", "eod"], default="intraday")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        bar = fetch_bar(args.ticker.upper(), args.timestamp, args.basis)
    except (HTTPError, URLError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    price_basis = (
        "alpaca-iex-minute-close" if args.basis == "intraday" else "alpaca-iex-eod-close"
    )
    print(f"ticker={args.ticker.upper()}")
    print(f"bar_timestamp={bar['t']}")
    print(f"execution_price_usd={bar['c']}")
    print(f"price_basis={price_basis}")
    print("note=estimate only; the bar close is not an actual execution fill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
