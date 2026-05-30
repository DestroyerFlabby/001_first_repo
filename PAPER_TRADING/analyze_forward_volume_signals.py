from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from analyze_volume_spikes import DailyBar, fetch_daily_bars, tracked_stock_tickers
from compare_investors import TSX_SYMBOLS


ROOT = Path(__file__).parent
RESEARCH_DIR = ROOT / "research"
START = date(2026, 1, 2)
CSV_FILE = RESEARCH_DIR / "tracked_stock_forward_volume_signals_since_2026-01-01.csv"
REPORT_FILE = RESEARCH_DIR / "tracked_stock_forward_volume_signals_since_2026-01-01.md"
FIELDS = [
    "ticker",
    "signal_date",
    "close",
    "prior_5d_return_pct",
    "prior_20d_return_pct",
    "prior_5d_volume_ratio",
    "prior_5d_up_sessions",
    "prior_5d_volume_up_sessions",
    "distance_to_20d_high_pct",
    "next_5d_avg_volume_ratio",
    "next_5d_peak_volume_ratio",
    "next_5d_max_return_pct",
]


@dataclass
class Observation:
    ticker: str
    day: date
    close: Decimal
    prior_5d_return_pct: Decimal
    prior_20d_return_pct: Decimal
    prior_5d_volume_ratio: Decimal
    prior_5d_up_sessions: int
    prior_5d_volume_up_sessions: int
    distance_to_20d_high_pct: Decimal
    next_5d_avg_volume_ratio: Decimal
    next_5d_peak_volume_ratio: Decimal
    next_5d_max_return_pct: Decimal


@dataclass
class Rule:
    name: str
    predicate: object


def average(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0")) / len(values)


def pct_change(value: Decimal, baseline: Decimal) -> Decimal:
    return (value / baseline - 1) * 100


def observe(ticker: str, bars: list[DailyBar]) -> list[Observation]:
    observations: list[Observation] = []
    for index in range(20, len(bars) - 5):
        current = bars[index]
        if current.day < START:
            continue
        prior_5 = bars[index - 5 : index]
        prior_20 = bars[index - 20 : index]
        next_5 = bars[index + 1 : index + 6]
        normal_volume = average([bar.volume for bar in prior_20])
        if normal_volume == 0:
            continue
        observations.append(
            Observation(
                ticker=ticker,
                day=current.day,
                close=current.close,
                prior_5d_return_pct=pct_change(current.close, prior_5[0].close),
                prior_20d_return_pct=pct_change(current.close, prior_20[0].close),
                prior_5d_volume_ratio=average([bar.volume for bar in prior_5])
                / normal_volume,
                prior_5d_up_sessions=sum(
                    bar.close > previous.close
                    for previous, bar in zip(
                        bars[index - 5 : index], bars[index - 4 : index + 1]
                    )
                ),
                prior_5d_volume_up_sessions=sum(
                    bar.volume > previous.volume
                    for previous, bar in zip(
                        bars[index - 5 : index], bars[index - 4 : index + 1]
                    )
                ),
                distance_to_20d_high_pct=pct_change(
                    current.close, max(bar.close for bar in prior_20)
                ),
                next_5d_avg_volume_ratio=average([bar.volume for bar in next_5])
                / normal_volume,
                next_5d_peak_volume_ratio=max(bar.volume for bar in next_5)
                / normal_volume,
                next_5d_max_return_pct=max(
                    pct_change(bar.close, current.close) for bar in next_5
                ),
            )
        )
    return observations


def live_row(ticker: str, bars: list[DailyBar]) -> dict[str, object] | None:
    if len(bars) < 21:
        return None
    current = bars[-1]
    prior_5 = bars[-6:-1]
    prior_20 = bars[-21:-1]
    normal_volume = average([bar.volume for bar in prior_20])
    if normal_volume == 0:
        return None
    volume_ratio = average([bar.volume for bar in prior_5]) / normal_volume
    return {
        "ticker": ticker,
        "day": current.day,
        "return_pct": pct_change(current.close, prior_5[0].close),
        "volume_ratio": volume_ratio,
        "distance_to_high_pct": pct_change(
            current.close, max(bar.close for bar in prior_20)
        ),
    }


def csv_row(row: Observation) -> dict[str, str]:
    def number(value: Decimal, places: str = "0.01") -> str:
        return str(value.quantize(Decimal(places)))

    return {
        "ticker": row.ticker,
        "signal_date": row.day.isoformat(),
        "close": number(row.close, "0.0001"),
        "prior_5d_return_pct": number(row.prior_5d_return_pct),
        "prior_20d_return_pct": number(row.prior_20d_return_pct),
        "prior_5d_volume_ratio": number(row.prior_5d_volume_ratio),
        "prior_5d_up_sessions": str(row.prior_5d_up_sessions),
        "prior_5d_volume_up_sessions": str(row.prior_5d_volume_up_sessions),
        "distance_to_20d_high_pct": number(row.distance_to_20d_high_pct),
        "next_5d_avg_volume_ratio": number(row.next_5d_avg_volume_ratio),
        "next_5d_peak_volume_ratio": number(row.next_5d_peak_volume_ratio),
        "next_5d_max_return_pct": number(row.next_5d_max_return_pct),
    }


def rules() -> list[Rule]:
    return [
        Rule("All observations", lambda _: True),
        Rule("5d volume >= 1.5x normal", lambda row: row.prior_5d_volume_ratio >= Decimal("1.5")),
        Rule("5d price return >= +10%", lambda row: row.prior_5d_return_pct >= Decimal("10")),
        Rule(
            "5d volume >= 1.5x and price >= +10%",
            lambda row: row.prior_5d_volume_ratio >= Decimal("1.5")
            and row.prior_5d_return_pct >= Decimal("10"),
        ),
        Rule(
            "Near 20d high and 5d volume >= 1.25x",
            lambda row: row.distance_to_20d_high_pct >= Decimal("-2")
            and row.prior_5d_volume_ratio >= Decimal("1.25"),
        ),
        Rule(
            "5d volume >= 1.5x, price >= +10%, near 20d high",
            lambda row: row.prior_5d_volume_ratio >= Decimal("1.5")
            and row.prior_5d_return_pct >= Decimal("10")
            and row.distance_to_20d_high_pct >= Decimal("-2"),
        ),
        Rule(
            "4+ rising-volume sessions and price >= +5%",
            lambda row: row.prior_5d_volume_up_sessions >= 4
            and row.prior_5d_return_pct >= Decimal("5"),
        ),
    ]


def stats(observations: list[Observation], rule: Rule) -> dict[str, object]:
    rows = [row for row in observations if rule.predicate(row)]
    if not rows:
        return {"name": rule.name, "count": 0}
    return {
        "name": rule.name,
        "count": len(rows),
        "avg_expansion": sum(row.next_5d_avg_volume_ratio >= Decimal("1.5") for row in rows),
        "peak_expansion": sum(row.next_5d_peak_volume_ratio >= Decimal("2") for row in rows),
        "median_avg": statistics.median(float(row.next_5d_avg_volume_ratio) for row in rows),
        "median_peak": statistics.median(float(row.next_5d_peak_volume_ratio) for row in rows),
        "median_return": statistics.median(float(row.next_5d_max_return_pct) for row in rows),
    }


def markdown(
    observations: list[Observation],
    live_rows: list[dict[str, object]],
    failures: list[str],
    universe_size: int,
) -> str:
    lines = [
        "# Forward Volume Signal Study for Tracked Stocks",
        "",
        f"Research snapshot generated: {date.today().isoformat()}",
        "",
        "## Question",
        "",
        "Which observable technical conditions were associated with elevated trading",
        "volume during the next five sessions?",
        "",
        "## Method",
        "",
        f"- Screened `{universe_size}` unique tracked stock tickers from `data/trades.csv`.",
        "- Used rolling daily observations from January 2, 2026 onward.",
        "- Used only information available by each observation date.",
        "- Defined normal volume as the prior 20-session average.",
        "- Defined future average-volume expansion as next-five-session average volume",
        "  at least `1.5x` normal.",
        "- Defined future peak-volume expansion as at least one of the next five sessions",
        "  reaching `2.0x` normal volume.",
        "- This is descriptive analysis on a selected tracked universe, not an",
        "  out-of-sample trading model.",
        "",
        "## Results",
        "",
        "| Pre-Existing Condition | Observations | Next 5d Avg Volume >=1.5x | Next 5d Peak Volume >=2x | Median Next Avg Volume | Median Next Peak Volume | Median Next 5d Max Return |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in (stats(observations, rule) for rule in rules()):
        count = item["count"]
        if not count:
            continue
        lines.append(
            f"| {item['name']} | `{count}` | `{item['avg_expansion'] / count * 100:.1f}%` | "
            f"`{item['peak_expansion'] / count * 100:.1f}%` | `{item['median_avg']:.2f}x` | "
            f"`{item['median_peak']:.2f}x` | `{item['median_return']:+.2f}%` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The practical watch condition is a combination: price strength near a",
            "recent high plus already-expanding volume. Rising volume without price",
            "strength is noisier, and price strength without volume offers less",
            "evidence that attention is broadening.",
            "",
            "For live screening, prioritize names where:",
            "",
            "1. Five-session return is at least `+10%`.",
            "2. Five-session average volume is at least `1.5x` the prior 20-session average.",
            "3. The close is within `2%` of its prior 20-session high.",
            "4. A company-specific catalyst can be identified separately.",
            "",
            "This flags names where additional volume is more plausible. It does not",
            "establish that the next price move will be positive.",
            "",
            "## Latest Live Screen",
            "",
            "The rows below use the latest available close and therefore do not have",
            "known next-five-session outcomes yet.",
            "",
            "| Ticker | As Of | Prior 5d Return | Prior 5d Volume Ratio | Distance to Prior 20d High | Strict Match |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for row in sorted(
        live_rows,
        key=lambda item: (item["strict"], item["volume_ratio"]),
        reverse=True,
    ):
        lines.append(
            f"| `{row['ticker']}` | {row['day']} | `{row['return_pct']:+.2f}%` | "
            f"`{row['volume_ratio']:.2f}x` | `{row['distance_to_high_pct']:+.2f}%` | "
            f"{'yes' if row['strict'] else 'near'} |"
        )
    if not live_rows:
        lines.append("| None | - | - | - | - | - |")
    lines.extend(
        [
            "",
            "## Data",
            "",
            "The sortable rolling observations are in",
            "`research/tracked_stock_forward_volume_signals_since_2026-01-01.csv`.",
            "",
            "Source: [Yahoo Finance](https://finance.yahoo.com/) public chart feed.",
        ]
    )
    if failures:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- `{failure}`" for failure in failures)
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    tickers = tracked_stock_tickers()
    observations: list[Observation] = []
    latest_rows: list[dict[str, object]] = []
    failures: list[str] = []
    for ticker in tickers:
        try:
            bars = fetch_daily_bars(TSX_SYMBOLS.get(ticker, ticker))
            observations.extend(observe(ticker, bars))
            latest = live_row(ticker, bars)
            if latest:
                strict = (
                    latest["return_pct"] >= Decimal("10")
                    and latest["volume_ratio"] >= Decimal("1.5")
                    and latest["distance_to_high_pct"] >= Decimal("-2")
                )
                near = (
                    latest["volume_ratio"] >= Decimal("1.25")
                    and latest["distance_to_high_pct"] >= Decimal("-2")
                )
                if strict or near:
                    latest_rows.append({**latest, "strict": strict})
        except Exception as exc:
            failures.append(f"{ticker}: {exc}")
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_FILE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(csv_row(row) for row in observations)
    REPORT_FILE.write_text(
        markdown(observations, latest_rows, failures, len(tickers)),
        encoding="utf-8",
    )
    print(f"Tracked stock tickers screened: {len(tickers)}")
    print(f"Rolling observations: {len(observations)}")
    print(f"Warnings: {len(failures)}")
    print(f"Wrote {CSV_FILE}")
    print(f"Wrote {REPORT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
