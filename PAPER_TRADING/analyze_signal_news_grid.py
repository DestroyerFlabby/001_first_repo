from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from itertools import product
from pathlib import Path

from backend.dashboard_service import (
    VARIABLE_ENTRY_USD,
    entry_signal,
    fetch_chart,
    live_signal,
    on_or_before,
    tracked_stock_assets,
    yahoo_symbol,
)
from backend.news_strategy import load_daily_news_counts, news_metrics


ROOT = Path(__file__).resolve().parent
GRID_START = date(2026, 1, 1)
TRAIN_END = date(2026, 3, 31)
REPORT_FILE = ROOT / "research" / "signal_news_grid_search_since_2026-01-01.md"
CSV_FILE = ROOT / "research" / "signal_news_grid_search_since_2026-01-01.csv"
ENTRY_SIGNAL_RULES = {
    "any-signal": {"fresh", "strict", "near"},
    "fresh-or-strict": {"fresh", "strict"},
    "fresh-only": {"fresh"},
    "strict-only": {"strict"},
}
ENTRY_NEWS_RULES = ("ignore", "active", "accelerating")
EXIT_NEWS_RULES = ("ignore", "cooling", "zero")
NONE_STREAKS = (5, 10, 15, 20)
MOMENTUM_CUTOFFS = (Decimal("0"), Decimal("-5"), Decimal("-10"))


@dataclass(frozen=True)
class Observation:
    category: str | None
    one_month_return: Decimal
    articles_7d: int
    articles_prior_7d: int
    close: Decimal


@dataclass(frozen=True)
class Strategy:
    entry_signal_rule: str
    entry_news_rule: str
    exit_news_rule: str
    none_streak: int
    momentum_cutoff: Decimal

    @property
    def label(self) -> str:
        return (
            f"entry={self.entry_signal_rule}; entry-news={self.entry_news_rule}; "
            f"exit={self.none_streak}none/{self.momentum_cutoff}%/{self.exit_news_rule}"
        )


def eligible_news(rule: str, row: Observation) -> bool:
    if rule == "ignore":
        return True
    if rule == "active":
        return row.articles_7d > 0
    if rule == "accelerating":
        return row.articles_7d > row.articles_prior_7d
    raise ValueError(f"unknown entry news rule: {rule}")


def exit_news_matches(rule: str, row: Observation) -> bool:
    if rule == "ignore":
        return True
    if rule == "cooling":
        return row.articles_7d <= row.articles_prior_7d
    if rule == "zero":
        return row.articles_7d == 0
    raise ValueError(f"unknown exit news rule: {rule}")


def build_observations(
    charts: dict[str, tuple[object, ...]],
    market_bars: tuple[object, ...],
    counts_by_ticker: dict[str, dict[str, int]],
    end: date,
) -> tuple[list[date], dict[date, dict[str, Observation]]]:
    sessions = [bar.day for bar in market_bars if GRID_START <= bar.day <= end]
    observations: dict[date, dict[str, Observation]] = {}
    previous_session = on_or_before(market_bars, GRID_START - timedelta(days=1))
    for session in sessions:
        if not previous_session:
            previous_session = on_or_before(market_bars, session - timedelta(days=1))
        daily: dict[str, Observation] = {}
        for ticker, bars in charts.items():
            price = on_or_before(bars, session)
            if not price:
                continue
            signal_bars = tuple(bar for bar in bars if bar.day <= previous_session.day)
            signal = live_signal(signal_bars)
            one_month = (signal or {}).get("horizons", {}).get("1m", {})
            news = news_metrics(counts_by_ticker.get(ticker, {}), previous_session.day)
            daily[ticker] = Observation(
                category=entry_signal(signal),
                one_month_return=Decimal(str(one_month.get("return_pct", "0"))),
                articles_7d=int(news["articles_7d"]),
                articles_prior_7d=int(news["articles_prior_7d"]),
                close=price.close,
            )
        observations[session] = daily
        previous_session = on_or_before(market_bars, session)
    return sessions, observations


def simulate(
    strategy: Strategy,
    sessions: list[date],
    observations: dict[date, dict[str, Observation]],
) -> dict[str, object]:
    active: dict[str, dict[str, object]] = {}
    closed_value = Decimal("0")
    deployed = Decimal("0")
    for session in sessions:
        rows = observations[session]
        technically_active = {
            ticker
            for ticker, row in rows.items()
            if row.category in ENTRY_SIGNAL_RULES[strategy.entry_signal_rule]
        }
        for ticker in set(active) & technically_active:
            active[ticker]["none_streak"] = 0
        for ticker in sorted(set(active) - technically_active):
            row = rows.get(ticker)
            if not row:
                continue
            position = active.pop(ticker)
            position["none_streak"] = int(position["none_streak"]) + 1
            should_exit = (
                int(position["none_streak"]) >= strategy.none_streak
                and row.one_month_return <= strategy.momentum_cutoff
                and exit_news_matches(strategy.exit_news_rule, row)
            )
            if not should_exit:
                active[ticker] = position
                continue
            closed_value += Decimal(str(position["shares"])) * row.close
        for ticker in sorted(technically_active - set(active)):
            row = rows[ticker]
            if not eligible_news(strategy.entry_news_rule, row):
                continue
            active[ticker] = {
                "shares": VARIABLE_ENTRY_USD / row.close,
                "none_streak": 0,
            }
            deployed += VARIABLE_ENTRY_USD
    ending = closed_value
    latest_rows = observations[sessions[-1]]
    for ticker, position in active.items():
        row = latest_rows.get(ticker)
        if row:
            ending += Decimal(str(position["shares"])) * row.close
    gain = ending - deployed
    return {
        "strategy": strategy.label,
        "entry_signal_rule": strategy.entry_signal_rule,
        "entry_news_rule": strategy.entry_news_rule,
        "exit_news_rule": strategy.exit_news_rule,
        "none_streak": strategy.none_streak,
        "momentum_cutoff": strategy.momentum_cutoff,
        "entries": int(deployed / VARIABLE_ENTRY_USD),
        "closed": int(deployed / VARIABLE_ENTRY_USD) - len(active),
        "open": len(active),
        "deployed": deployed,
        "ending": ending,
        "gain": gain,
        "return_pct": gain / deployed * 100 if deployed else Decimal("0"),
    }


def write_results(rows: list[dict[str, object]], counts_to_date: str | None, end: date) -> None:
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CSV_FILE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Signal And News Grid Search Since 2026-01-01",
        "",
        "## Scope",
        "",
        f"- Simulated window: `{GRID_START.isoformat()}` to `{end.isoformat()}`.",
        f"- Committed Alpaca daily news counts currently end on `{counts_to_date}`.",
        f"- Tested combinations: `{len(rows)}`.",
        "- Signals and news use information visible by the prior close. Trades execute at the next available close.",
        "- The top rows are optimized on this same historical sample. They are hypotheses for forward tracking, not validated predictions.",
        "",
        "## Top 20 By Return",
        "",
        f"- Train/test reference split: `{GRID_START.isoformat()}` to `{TRAIN_END.isoformat()}` and `{(TRAIN_END + timedelta(days=1)).isoformat()}` to `{end.isoformat()}`.",
        "",
        "| Rank | Entry signal | Entry news | Exit news | Missing-signal sessions | 1m cutoff | Entries | Gain | Full return | Train return | Test return |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, row in enumerate(rows[:20], start=1):
        lines.append(
            f"| {rank} | {row['entry_signal_rule']} | {row['entry_news_rule']} | "
            f"{row['exit_news_rule']} | {row['none_streak']} | {row['momentum_cutoff']}% | "
            f"{row['entries']} | ${row['gain']:,.2f} | {row['return_pct']:.2f}% |"
            f" {row['train_return_pct']:.2f}% | {row['test_return_pct']:.2f}% |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "Use this ranking to select a small number of forward-tracking candidates. Do not promote the highest-return row directly into a live rule: testing hundreds of combinations creates overfitting risk.",
        "",
        f"The full sortable result set is in `{CSV_FILE.relative_to(ROOT)}`.",
        "",
    ]
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    _, market_bars = fetch_chart("SPY")
    end_bar = on_or_before(market_bars, None)
    if not end_bar:
        raise RuntimeError("missing ending market close")
    charts: dict[str, tuple[object, ...]] = {}
    for ticker, security_type in tracked_stock_assets():
        try:
            _, bars = fetch_chart(yahoo_symbol(ticker, security_type))
        except Exception:
            continue
        if bars:
            charts[ticker] = bars
    payload = load_daily_news_counts()
    raw_counts = payload.get("tickers", {})
    counts_by_ticker = raw_counts if isinstance(raw_counts, dict) else {}
    sessions, observations = build_observations(
        charts,
        market_bars,
        counts_by_ticker,
        end_bar.day,
    )
    strategies = [
        Strategy(*values)
        for values in product(
            ENTRY_SIGNAL_RULES,
            ENTRY_NEWS_RULES,
            EXIT_NEWS_RULES,
            NONE_STREAKS,
            MOMENTUM_CUTOFFS,
        )
    ]
    train_sessions = [session for session in sessions if session <= TRAIN_END]
    test_sessions = [session for session in sessions if session > TRAIN_END]
    rows = []
    for strategy in strategies:
        row = simulate(strategy, sessions, observations)
        train = simulate(strategy, train_sessions, observations)
        test = simulate(strategy, test_sessions, observations)
        row["train_return_pct"] = train["return_pct"]
        row["test_return_pct"] = test["return_pct"]
        rows.append(row)
    rows.sort(key=lambda row: (row["return_pct"], row["gain"]), reverse=True)
    write_results(rows, payload.get("to_date"), end_bar.day)
    print(f"Tested {len(rows)} combinations from {GRID_START} to {end_bar.day}.")
    for rank, row in enumerate(rows[:10], start=1):
        print(f"{rank}. {row['strategy']}: gain=${row['gain']:,.2f} return={row['return_pct']:.2f}%")
    print(f"Wrote {REPORT_FILE}")
    print(f"Wrote {CSV_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
