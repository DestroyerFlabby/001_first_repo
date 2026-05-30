from __future__ import annotations

import argparse
import csv
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen

from analyze_forward_volume_signals import average, pct_change
from analyze_volume_spikes import DailyBar, fetch_daily_bars
from paper_trading import FIELDNAMES, TRADES_FILE


ROOT = Path(__file__).parent
RESEARCH_DIR = ROOT / "research"
NASDAQ_SCREENER_URL = (
    "https://api.nasdaq.com/api/screener/stocks"
    "?tableonly=true&limit=25&offset=0&download=true"
)
EXCLUDED_NAME_TERMS = (
    " ETF",
    " ETN",
    " Fund",
    " Warrant",
    " Warrants",
    " Rights",
    " Units",
    " Unit ",
    " Preferred",
    " Depositary Shares",
    " Notes",
    " Note ",
    " Bond",
    " Trust Beneficial",
    " Acquisition Corp",
    " Acquisition Corporation",
    " Income Shares",
    " Closed End",
)
CSV_FIELDS = [
    "rank",
    "ticker",
    "company",
    "sector",
    "industry",
    "latest_date",
    "latest_close",
    "market_cap_usd",
    "latest_volume",
    "prior_5d_return_pct",
    "prior_20d_return_pct",
    "prior_5d_volume_ratio",
    "prior_5d_volume_up_sessions",
    "distance_to_20d_high_pct",
    "score",
]


@dataclass
class Candidate:
    ticker: str
    company: str
    sector: str
    industry: str
    day: date
    close: Decimal
    market_cap_usd: Decimal
    latest_volume: Decimal
    prior_5d_return_pct: Decimal
    prior_20d_return_pct: Decimal
    prior_5d_volume_ratio: Decimal
    prior_5d_volume_up_sessions: int
    distance_to_20d_high_pct: Decimal
    score: Decimal


def decimal(value: str | None) -> Decimal:
    return Decimal((value or "0").replace("$", "").replace(",", ""))


def clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return max(low, min(value, high))


def next_weekday(day: date) -> date:
    day += timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def latest_weekday(day: date) -> date:
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def fetch_nasdaq_rows() -> list[dict[str, str]]:
    request = Request(
        NASDAQ_SCREENER_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.nasdaq.com",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)["data"]["rows"]


def eligible_nasdaq_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    eligible = []
    for row in rows:
        ticker = row["symbol"].strip()
        company = row["name"] or ""
        price = decimal(row.get("lastsale"))
        latest_volume = decimal(row.get("volume"))
        market_cap = decimal(row.get("marketCap"))
        if not re.fullmatch(r"[A-Z]{1,5}", ticker):
            continue
        if not Decimal("10") <= price <= Decimal("50"):
            continue
        if latest_volume < Decimal("100000") or market_cap < Decimal("100000000"):
            continue
        if any(term.casefold() in company.casefold() for term in EXCLUDED_NAME_TERMS):
            continue
        eligible.append(row)
    return eligible


def analyze(row: dict[str, str]) -> Candidate | None:
    ticker = row["symbol"].strip()
    bars = fetch_daily_bars(ticker)
    if len(bars) < 21:
        return None
    current = bars[-1]
    prior_5 = bars[-6:-1]
    prior_20 = bars[-21:-1]
    normal_volume = average([bar.volume for bar in prior_20])
    if normal_volume == 0:
        return None
    return_5d = pct_change(current.close, prior_5[0].close)
    return_20d = pct_change(current.close, prior_20[0].close)
    volume_ratio = average([bar.volume for bar in prior_5]) / normal_volume
    distance_to_high = pct_change(current.close, max(bar.close for bar in prior_20))
    rising_volume_sessions = sum(
        bar.volume > previous.volume
        for previous, bar in zip(bars[-6:-1], bars[-5:])
    )

    # Fresh setup filter: attention is rising, but the stock has not already
    # completed an extreme short-term repricing.
    if not Decimal("3") <= return_5d <= Decimal("25"):
        return None
    if not Decimal("5") <= return_20d <= Decimal("40"):
        return None
    if volume_ratio < Decimal("1.25"):
        return None
    if not Decimal("-3") <= distance_to_high <= Decimal("8"):
        return None

    momentum_score = Decimal("30") * clamp(return_5d, Decimal("3"), Decimal("20")) / 20
    volume_score = Decimal("35") * clamp(volume_ratio - 1, Decimal("0"), Decimal("1")) 
    breakout_score = Decimal("20") * clamp(distance_to_high + 3, Decimal("0"), Decimal("8")) / 8
    persistence_score = Decimal("15") * Decimal(rising_volume_sessions) / 5
    score = momentum_score + volume_score + breakout_score + persistence_score
    return Candidate(
        ticker=ticker,
        company=row["name"] or "",
        sector=row.get("sector") or "",
        industry=row.get("industry") or "",
        day=current.day,
        close=current.close,
        market_cap_usd=decimal(row.get("marketCap")),
        latest_volume=decimal(row.get("volume")),
        prior_5d_return_pct=return_5d,
        prior_20d_return_pct=return_20d,
        prior_5d_volume_ratio=volume_ratio,
        prior_5d_volume_up_sessions=rising_volume_sessions,
        distance_to_20d_high_pct=distance_to_high,
        score=score,
    )


def csv_row(rank: int, row: Candidate) -> dict[str, str]:
    def number(value: Decimal, places: str = "0.01") -> str:
        return str(value.quantize(Decimal(places)))

    return {
        "rank": str(rank),
        "ticker": row.ticker,
        "company": row.company,
        "sector": row.sector,
        "industry": row.industry,
        "latest_date": row.day.isoformat(),
        "latest_close": number(row.close, "0.0001"),
        "market_cap_usd": number(row.market_cap_usd, "0"),
        "latest_volume": number(row.latest_volume, "0"),
        "prior_5d_return_pct": number(row.prior_5d_return_pct),
        "prior_20d_return_pct": number(row.prior_20d_return_pct),
        "prior_5d_volume_ratio": number(row.prior_5d_volume_ratio),
        "prior_5d_volume_up_sessions": str(row.prior_5d_volume_up_sessions),
        "distance_to_20d_high_pct": number(row.distance_to_20d_high_pct),
        "score": number(row.score),
    }


def load_snapshot(path: Path) -> list[Candidate]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        Candidate(
            ticker=row["ticker"],
            company=row["company"],
            sector=row["sector"],
            industry=row["industry"],
            day=date.fromisoformat(row["latest_date"]),
            close=Decimal(row["latest_close"]),
            market_cap_usd=Decimal(row["market_cap_usd"]),
            latest_volume=Decimal(row["latest_volume"]),
            prior_5d_return_pct=Decimal(row["prior_5d_return_pct"]),
            prior_20d_return_pct=Decimal(row["prior_20d_return_pct"]),
            prior_5d_volume_ratio=Decimal(row["prior_5d_volume_ratio"]),
            prior_5d_volume_up_sessions=int(row["prior_5d_volume_up_sessions"]),
            distance_to_20d_high_pct=Decimal(row["distance_to_20d_high_pct"]),
            score=Decimal(row["score"]),
        )
        for row in rows
    ]


def reusable_snapshot() -> Path | None:
    snapshots = sorted(RESEARCH_DIR.glob("daily_fresh_setups_*.csv"))
    if not snapshots:
        return None
    latest = snapshots[-1]
    snapshot_day = date.fromisoformat(latest.stem.removeprefix("daily_fresh_setups_"))
    return latest if snapshot_day >= latest_weekday(date.today()) else None


def write_snapshot(rows: list[Candidate], universe_size: int, screened_size: int) -> tuple[Path, Path]:
    as_of = rows[0].day if rows else date.today()
    csv_file = RESEARCH_DIR / f"daily_fresh_setups_{as_of}.csv"
    md_file = RESEARCH_DIR / f"daily_fresh_setups_{as_of}.md"
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(csv_row(rank, row) for rank, row in enumerate(rows, start=1))

    lines = [
        f"# Daily Fresh Setups: {as_of}",
        "",
        f"Prepared for the next weekday session: {next_weekday(as_of)}",
        "",
        "## Method",
        "",
        f"- Started from `{universe_size}` Nasdaq screener rows.",
        f"- Evaluated `{screened_size}` liquid `$10-50` common-stock candidates.",
        "- Excluded names with five-session gains above `25%` or 20-session gains",
        "  above `40%` to avoid chasing already-extended moves.",
        "- Required five-session volume of at least `1.25x` the prior 20-session",
        "  average and a price within `3%` below to `8%` above the prior 20-session high.",
        "- Ranked remaining names using momentum, relative volume, breakout position,",
        "  and the number of rising-volume sessions.",
        "- This is a research screen, not a recommendation or automated trade signal.",
        "",
        "## Portfolio Candidates",
        "",
        "| Rank | Ticker | Price | Score | 5d Return | 20d Return | 5d Volume | Distance to 20d High | Sector |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, row in enumerate(rows, start=1):
        lines.append(
            f"| {rank} | `{row.ticker}` | `${row.close:.2f}` | `{row.score:.2f}` | "
            f"`{row.prior_5d_return_pct:+.2f}%` | `{row.prior_20d_return_pct:+.2f}%` | "
            f"`{row.prior_5d_volume_ratio:.2f}x` | `{row.distance_to_20d_high_pct:+.2f}%` | "
            f"{row.sector or '-'} |"
        )
    if not rows:
        lines.append("| - | None | - | - | - | - | - | - | - |")
    lines.extend(
        [
            "",
            "## Sources",
            "",
            "- [Nasdaq stock screener](https://www.nasdaq.com/market-activity/stocks/screener)",
            "- [Yahoo Finance](https://finance.yahoo.com/) public chart feed",
            "",
        ]
    )
    md_file.write_text("\n".join(lines), encoding="utf-8")
    return csv_file, md_file


def record_portfolio(rows: list[Candidate], investor: str) -> int:
    with TRADES_FILE.open(newline="", encoding="utf-8-sig") as handle:
        existing_rows = list(csv.DictReader(handle))
    existing = {
        row["ticker"]
        for row in existing_rows
        if row["investor"].casefold() == investor.casefold()
    }
    additions = [row for row in rows if row.ticker not in existing]
    with TRADES_FILE.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        for row in additions:
            writer.writerow(
                {
                    "trade_id": uuid.uuid4().hex[:12],
                    "timestamp": f"{row.day.isoformat()}T16:00:00-04:00",
                    "investor": investor,
                    "ticker": row.ticker,
                    "security_type": "stock",
                    "side": "buy",
                    "usd_amount": "1000",
                    "amount_basis": "default-stock",
                    "execution_price_usd": str(row.close),
                    "price_basis": "reported-fill",
                    "notes": (
                        "Daily fresh-setup scan; forward benchmark; "
                        f"score={row.score.quantize(Decimal('0.01'))}; "
                        f"next weekday session={next_weekday(row.day)}"
                    ),
                }
            )
    return len(additions)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Screen fresh $10-50 stock setups.")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force a new broad-market download instead of reusing today's snapshot.",
    )
    parser.add_argument(
        "--record-portfolio",
        action="store_true",
        help="Append the selected rows to the paper-trading ledger.",
    )
    parser.add_argument(
        "--investor",
        help="Portfolio name for --record-portfolio. Defaults to daily-watchlist-<next weekday>.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    snapshot = reusable_snapshot()
    if snapshot and not args.refresh:
        selected = load_snapshot(snapshot)[: args.top]
        csv_file = snapshot
        md_file = snapshot.with_suffix(".md")
        print(f"Reused same-day snapshot: {snapshot}")
    else:
        nasdaq_rows = fetch_nasdaq_rows()
        eligible = eligible_nasdaq_rows(nasdaq_rows)
        candidates: list[Candidate] = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(analyze, row) for row in eligible]
            for future in as_completed(futures):
                try:
                    candidate = future.result()
                except Exception:
                    continue
                if candidate:
                    candidates.append(candidate)
        selected = sorted(candidates, key=lambda row: row.score, reverse=True)[: args.top]
        csv_file, md_file = write_snapshot(selected, len(nasdaq_rows), len(eligible))
        print(f"Nasdaq rows: {len(nasdaq_rows)}")
        print(f"Eligible liquid $10-50 common stocks: {len(eligible)}")
        print(f"Fresh setups: {len(candidates)}")
    print(f"Selected rows: {len(selected)}")
    for rank, row in enumerate(selected, start=1):
        print(
            f"{rank:>2}. {row.ticker:<5} ${row.close:>7.2f} score={row.score:>6.2f} "
            f"5d={row.prior_5d_return_pct:+6.2f}% volume={row.prior_5d_volume_ratio:.2f}x"
        )
    print(f"Wrote {csv_file}")
    print(f"Wrote {md_file}")
    if args.record_portfolio:
        if selected:
            investor = args.investor or f"daily-watchlist-{next_weekday(selected[0].day)}"
            additions = record_portfolio(selected, investor)
            print(f"Recorded {additions} new positions for {investor}")
        else:
            print("No portfolio recorded because no fresh setups matched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
