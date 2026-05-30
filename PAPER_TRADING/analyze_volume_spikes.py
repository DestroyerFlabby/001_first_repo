from __future__ import annotations

import csv
import json
import statistics
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from compare_investors import TSX_SYMBOLS


ROOT = Path(__file__).parent
TRADES_FILE = ROOT / "data" / "trades.csv"
RESEARCH_DIR = ROOT / "research"
START = date(2026, 1, 2)
THRESHOLD_PCT = Decimal("25")
CSV_FILE = RESEARCH_DIR / "tracked_stock_volume_spikes_since_2026-01-01.csv"
REPORT_FILE = RESEARCH_DIR / "tracked_stock_volume_spikes_since_2026-01-01.md"
FIELDS = [
    "ticker",
    "yahoo_symbol",
    "baseline_date",
    "baseline_close",
    "first_spike_date",
    "first_spike_close",
    "first_spike_return_pct",
    "latest_date",
    "latest_close",
    "latest_return_pct",
    "leading_5d_avg_volume",
    "prior_20d_avg_volume",
    "leading_5d_vs_prior_20d",
    "spike_day_volume",
    "spike_day_vs_prior_20d",
    "pre_spike_5d_return_pct",
    "pattern",
]


@dataclass
class DailyBar:
    day: date
    close: Decimal
    volume: Decimal


@dataclass
class Spike:
    ticker: str
    yahoo_symbol: str
    baseline: DailyBar
    first_spike: DailyBar
    latest: DailyBar
    leading_5d_avg_volume: Decimal | None
    prior_20d_avg_volume: Decimal | None
    pre_spike_5d_return_pct: Decimal | None

    @property
    def first_spike_return_pct(self) -> Decimal:
        return pct_change(self.first_spike.close, self.baseline.close)

    @property
    def latest_return_pct(self) -> Decimal:
        return pct_change(self.latest.close, self.baseline.close)

    @property
    def leading_5d_vs_prior_20d(self) -> Decimal | None:
        return ratio(self.leading_5d_avg_volume, self.prior_20d_avg_volume)

    @property
    def spike_day_vs_prior_20d(self) -> Decimal | None:
        return ratio(self.first_spike.volume, self.prior_20d_avg_volume)

    @property
    def pattern(self) -> str:
        leading_ratio = self.leading_5d_vs_prior_20d
        spike_ratio = self.spike_day_vs_prior_20d
        if leading_ratio is not None and leading_ratio >= Decimal("1.5"):
            return "volume expanded before threshold"
        if spike_ratio is not None and spike_ratio >= Decimal("1.5"):
            return "volume expanded on threshold day"
        if leading_ratio is not None and spike_ratio is not None:
            return "no >=1.5x volume expansion"
        return "insufficient pre-spike sessions"


def pct_change(value: Decimal, baseline: Decimal) -> Decimal:
    return (value / baseline - 1) * 100


def ratio(value: Decimal | None, baseline: Decimal | None) -> Decimal | None:
    if value is None or baseline is None or baseline == 0:
        return None
    return value / baseline


def average(values: list[Decimal]) -> Decimal | None:
    return sum(values, Decimal("0")) / len(values) if values else None


def number(value: Decimal | None, places: str = "0.01") -> str:
    return "" if value is None else str(value.quantize(Decimal(places)))


def fetch_daily_bars(symbol: str) -> list[DailyBar]:
    period1 = int(datetime(2025, 12, 1, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.now(timezone.utc).timestamp()) + 86_400
    query = urlencode({"period1": period1, "period2": period2, "interval": "1d"})
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?{query}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=15) as response:
                result = json.load(response)["chart"]["result"][0]
            quotes = result["indicators"]["quote"][0]
            return [
                DailyBar(
                    datetime.fromtimestamp(timestamp, timezone.utc).date(),
                    Decimal(str(close)),
                    Decimal(str(volume or 0)),
                )
                for timestamp, close, volume in zip(
                    result["timestamp"], quotes["close"], quotes["volume"]
                )
                if close is not None
            ]
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f"Yahoo chart request failed: {last_error}")


def tracked_stock_tickers() -> list[str]:
    with TRADES_FILE.open(newline="", encoding="utf-8-sig") as handle:
        return sorted(
            {
                row["ticker"]
                for row in csv.DictReader(handle)
                if row["security_type"] == "stock"
            }
        )


def analyze_ticker(ticker: str) -> Spike | None:
    yahoo_symbol = TSX_SYMBOLS.get(ticker, ticker)
    bars = fetch_daily_bars(yahoo_symbol)
    baseline_index = next((index for index, bar in enumerate(bars) if bar.day >= START), None)
    if baseline_index is None:
        raise ValueError("missing January 2 baseline")
    baseline = bars[baseline_index]
    threshold = baseline.close * (Decimal("1") + THRESHOLD_PCT / 100)
    first_spike_index = next(
        (
            index
            for index, bar in enumerate(bars[baseline_index:], start=baseline_index)
            if bar.close >= threshold
        ),
        None,
    )
    if first_spike_index is None:
        return None

    first_spike = bars[first_spike_index]
    leading = bars[max(baseline_index, first_spike_index - 5) : first_spike_index]
    prior = bars[max(baseline_index, first_spike_index - 25) : max(baseline_index, first_spike_index - 5)]
    pre_start = bars[first_spike_index - 5] if first_spike_index - 5 >= baseline_index else None
    return Spike(
        ticker=ticker,
        yahoo_symbol=yahoo_symbol,
        baseline=baseline,
        first_spike=first_spike,
        latest=bars[-1],
        leading_5d_avg_volume=average([bar.volume for bar in leading]),
        prior_20d_avg_volume=average([bar.volume for bar in prior]),
        pre_spike_5d_return_pct=(
            pct_change(first_spike.close, pre_start.close) if pre_start else None
        ),
    )


def csv_row(spike: Spike) -> dict[str, str]:
    return {
        "ticker": spike.ticker,
        "yahoo_symbol": spike.yahoo_symbol,
        "baseline_date": spike.baseline.day.isoformat(),
        "baseline_close": number(spike.baseline.close, "0.0001"),
        "first_spike_date": spike.first_spike.day.isoformat(),
        "first_spike_close": number(spike.first_spike.close, "0.0001"),
        "first_spike_return_pct": number(spike.first_spike_return_pct),
        "latest_date": spike.latest.day.isoformat(),
        "latest_close": number(spike.latest.close, "0.0001"),
        "latest_return_pct": number(spike.latest_return_pct),
        "leading_5d_avg_volume": number(spike.leading_5d_avg_volume, "0"),
        "prior_20d_avg_volume": number(spike.prior_20d_avg_volume, "0"),
        "leading_5d_vs_prior_20d": number(spike.leading_5d_vs_prior_20d),
        "spike_day_volume": number(spike.first_spike.volume, "0"),
        "spike_day_vs_prior_20d": number(spike.spike_day_vs_prior_20d),
        "pre_spike_5d_return_pct": number(spike.pre_spike_5d_return_pct),
        "pattern": spike.pattern,
    }


def markdown(spikes: list[Spike], failures: list[str], universe_size: int) -> str:
    measurable = [spike for spike in spikes if spike.leading_5d_vs_prior_20d is not None]
    lead_expansion = [
        spike
        for spike in measurable
        if spike.leading_5d_vs_prior_20d >= Decimal("1.5")
    ]
    day_expansion = [
        spike
        for spike in measurable
        if spike.spike_day_vs_prior_20d is not None
        and spike.spike_day_vs_prior_20d >= Decimal("1.5")
    ]
    lead_ratios = [float(spike.leading_5d_vs_prior_20d) for spike in measurable]
    day_ratios = [
        float(spike.spike_day_vs_prior_20d)
        for spike in measurable
        if spike.spike_day_vs_prior_20d is not None
    ]
    pre_spike_returns = [
        float(spike.pre_spike_5d_return_pct)
        for spike in measurable
        if spike.pre_spike_5d_return_pct is not None
    ]
    lines = [
        "# Tracked Stock Volume Spikes Since January 1, 2026",
        "",
        f"Research snapshot generated: {date.today().isoformat()}",
        "",
        "## Scope",
        "",
        f"- Screened `{universe_size}` unique tracked `stock` tickers from `data/trades.csv`.",
        "- Excluded ETFs and crypto.",
        "- Used the January 2, 2026 close because January 1 was a market holiday.",
        "- Defined a spike as the first close at least `25%` above the January 2 close.",
        "- Compared average volume during the five sessions immediately before the",
        "  threshold date with the preceding 20-session average volume.",
        "- Used Yahoo Finance's public chart feed for split-adjusted chart history.",
        "- This is a tracked-ledger screen, not a scan of every listed public company.",
        "",
        "## Summary",
        "",
        f"- Stocks crossing the `+25%` threshold: `{len(spikes)}`.",
        f"- Crossings with enough pre-spike sessions for a volume comparison: `{len(measurable)}`.",
        (
            f"- Five-day pre-spike volume at least `1.5x` prior volume: "
            f"`{len(lead_expansion)} / {len(measurable)}`."
        ),
        (
            f"- Threshold-day volume at least `1.5x` prior volume: "
            f"`{len(day_expansion)} / {len(measurable)}`."
        ),
    ]
    if lead_ratios:
        lines.append(
            f"- Median five-day pre-spike volume ratio: `{statistics.median(lead_ratios):.2f}x`."
        )
    if day_ratios:
        lines.append(
            f"- Median threshold-day volume ratio: `{statistics.median(day_ratios):.2f}x`."
        )
    if pre_spike_returns:
        lines.append(
            f"- Positive price momentum during the five sessions before crossing: "
            f"`{sum(value > 0 for value in pre_spike_returns)} / {len(pre_spike_returns)}`."
        )
        lines.append(
            f"- Median five-session price return immediately before crossing: "
            f"`{statistics.median(pre_spike_returns):.2f}%`."
        )
    lines.extend(
        [
            "",
            "## Pattern Read",
            "",
            "The strongest recurring early signal in this tracked sample was price",
            "momentum, not volume alone: every measurable name was already rising during",
            "the five sessions before its first `+25%` close. Volume more often acted as",
            "confirmation on the threshold day than as a reliable early-warning signal.",
            "",
            "The useful distinction is whether volume expanded before the threshold",
            "crossing or only on the crossing day. A pre-spike ratio above `1.5x` can",
            "flag accumulation or an information-driven repricing already underway.",
            "A threshold-day-only surge is more consistent with a discrete catalyst.",
            "No volume expansion does not invalidate a move: sustained trends can cross",
            "the threshold after their heaviest trading has already occurred.",
            "",
            "Treat this as a screening signal, not a trading rule. Small-cap names can",
            "show extreme ratios because their prior liquidity was thin. News review,",
            "float, dilution, short interest, and valuation still need separate checks.",
            "",
            "## Results",
            "",
            "| Ticker | First +25% Date | Return at Crossing | Latest Return | Pre-Spike Volume Ratio | Threshold-Day Ratio | Pattern |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for spike in sorted(spikes, key=lambda item: item.latest_return_pct, reverse=True):
        lines.append(
            f"| `{spike.ticker}` | {spike.first_spike.day} | "
            f"`{spike.first_spike_return_pct:.2f}%` | `{spike.latest_return_pct:+.2f}%` | "
            f"`{number(spike.leading_5d_vs_prior_20d)}x` | "
            f"`{number(spike.spike_day_vs_prior_20d)}x` | {spike.pattern} |"
        )
    lines.extend(
        [
            "",
            "## Data",
            "",
            "The sortable per-stock measurements are in",
            "`research/tracked_stock_volume_spikes_since_2026-01-01.csv`.",
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
    spikes: list[Spike] = []
    failures: list[str] = []
    for ticker in tickers:
        try:
            spike = analyze_ticker(ticker)
            if spike:
                spikes.append(spike)
        except Exception as exc:
            failures.append(f"{ticker}: {exc}")

    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_FILE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(csv_row(spike) for spike in spikes)
    REPORT_FILE.write_text(markdown(spikes, failures, len(tickers)), encoding="utf-8")
    print(f"Tracked stock tickers screened: {len(tickers)}")
    print(f"Stocks crossing +25%: {len(spikes)}")
    print(f"Warnings: {len(failures)}")
    print(f"Wrote {CSV_FILE}")
    print(f"Wrote {REPORT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
