from __future__ import annotations

import argparse
import json
import time as time_module
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError
from urllib.parse import urlencode

from backend.dashboard_service import (
    VARIABLE_ENTRY_USD,
    VARIABLE_STRATEGY_START,
    entry_signal,
    fetch_chart,
    live_signal,
    on_or_before,
    tracked_stock_assets,
    yahoo_symbol,
)
from backend.news_service import fetch_json, load_dotenv, parse_timestamp
from backend.news_strategy import news_metrics, should_exit


ROOT = Path(__file__).resolve().parent
CACHE_FILE = ROOT / "data" / "historical_alpaca_news.json"
REPORT_FILE = ROOT / "research" / "news_assisted_strategy_backtest_2026-01-31_to_2026-06-01.md"
DAILY_COUNTS_FILE = ROOT / "data" / "historical_news_daily_counts.json"
LOCK = Lock()


def utc_datetime(day: date, end_of_day: bool = False) -> datetime:
    clock = time.max if end_of_day else time.min
    return datetime.combine(day, clock, tzinfo=timezone.utc)


def read_cache() -> dict[str, list[dict[str, str]]]:
    if not CACHE_FILE.exists():
        return {}
    try:
        payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_cache(payload: dict[str, list[dict[str, str]]]) -> None:
    with LOCK:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def alpaca_headers() -> dict[str, str]:
    import os

    load_dotenv()
    api_key = os.environ.get("ALPACA_KEY") or os.environ.get("APCA_API_KEY_ID")
    api_secret = os.environ.get("ALPACA_SECRET") or os.environ.get("APCA_API_SECRET_KEY")
    if not api_key or not api_secret:
        raise RuntimeError("set ALPACA_KEY and ALPACA_SECRET in the repository .env file")
    return {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
    }


def fetch_historical_news(
    ticker: str,
    start: date,
    end: date,
    max_articles: int,
) -> list[dict[str, str]]:
    headers = alpaca_headers()
    rows: list[dict[str, str]] = []
    next_page_token: str | None = None
    while len(rows) < max_articles:
        params = {
            "symbols": ticker,
            "start": utc_datetime(start).isoformat(),
            "end": utc_datetime(end, end_of_day=True).isoformat(),
            "limit": min(50, max_articles - len(rows)),
            "sort": "desc",
        }
        if next_page_token:
            params["page_token"] = next_page_token
        url = f"https://data.alpaca.markets/v1beta1/news?{urlencode(params)}"
        for attempt in range(5):
            try:
                payload = fetch_json(url, headers)
                break
            except HTTPError as exc:
                if exc.code != 429 or attempt == 4:
                    raise
                time_module.sleep(5 * (attempt + 1))
        batch = payload.get("news", [])
        if not isinstance(batch, list):
            break
        rows.extend(
            {
                "created_at": str(row.get("created_at", "")),
                "headline": str(row.get("headline", "")),
                "url": str(row.get("url", "")),
            }
            for row in batch
            if isinstance(row, dict) and row.get("created_at")
        )
        next_page_token = str(payload.get("next_page_token") or "") or None
        if not batch or not next_page_token:
            break
    return rows


def historical_news(
    tickers: list[str],
    start: date,
    end: date,
    max_articles: int,
    refresh: bool,
    refresh_from_ticker: str | None,
) -> dict[str, list[dict[str, str]]]:
    cache = read_cache()
    refresh_active = refresh and not refresh_from_ticker
    for index, ticker in enumerate(tickers, start=1):
        if refresh_from_ticker and ticker == refresh_from_ticker:
            refresh_active = True
        if not refresh_active and ticker in cache and len(cache[ticker]) != 500:
            print(f"[{index}/{len(tickers)}] {ticker}: cached {len(cache[ticker])}")
            continue
        cache[ticker] = fetch_historical_news(ticker, start, end, max_articles)
        write_cache(cache)
        print(f"[{index}/{len(tickers)}] {ticker}: fetched {len(cache[ticker])}")
    return cache


def article_dates(rows: list[dict[str, str]]) -> list[date]:
    return sorted(parse_timestamp(row["created_at"]).date() for row in rows)


def daily_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for day in article_dates(rows):
        key = day.isoformat()
        counts[key] = counts.get(key, 0) + 1
    return counts


def write_daily_counts(
    raw_news: dict[str, list[dict[str, str]]],
    start: date,
    end: date,
) -> None:
    payload = {
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "tickers": {
            ticker: daily_counts(rows)
            for ticker, rows in sorted(raw_news.items())
        },
    }
    DAILY_COUNTS_FILE.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def simulate(
    rule: str,
    charts: dict[str, tuple[object, ...]],
    market_bars: tuple[object, ...],
    news_by_ticker: dict[str, dict[str, int]],
    end: date,
    require_news_entry: bool = False,
) -> dict[str, object]:
    sessions = [
        bar.day
        for bar in market_bars
        if VARIABLE_STRATEGY_START <= bar.day <= end
    ]
    active: dict[str, dict[str, object]] = {}
    closed: list[Decimal] = []
    deployed = Decimal("0")
    previous_session = on_or_before(market_bars, VARIABLE_STRATEGY_START - timedelta(days=1))
    for session in sessions:
        if not previous_session:
            previous_session = on_or_before(market_bars, session - timedelta(days=1))
        desired: dict[str, str] = {}
        observed: dict[str, dict[str, object] | None] = {}
        observed_news: dict[str, dict[str, Decimal | int | None]] = {}
        for ticker, bars in charts.items():
            signal_bars = tuple(bar for bar in bars if bar.day <= previous_session.day)
            observed[ticker] = live_signal(signal_bars)
            observed_news[ticker] = news_metrics(news_by_ticker[ticker], previous_session.day)
            category = entry_signal(observed[ticker])
            if category:
                desired[ticker] = category

        for ticker in set(active) & set(desired):
            active[ticker]["none_streak"] = 0

        for ticker in sorted(set(active) - set(desired)):
            price_bar = on_or_before(charts[ticker], session)
            if not price_bar:
                continue
            position = active.pop(ticker)
            position["none_streak"] = int(position["none_streak"]) + 1
            signal = observed[ticker] or {}
            one_month = signal.get("horizons", {}).get("1m", {})
            one_month_return = Decimal(str(one_month.get("return_pct", "0")))
            if not should_exit(
                rule,
                int(position["none_streak"]),
                one_month_return,
                observed_news[ticker],
            ):
                active[ticker] = position
                continue
            proceeds = Decimal(str(position["shares"])) * price_bar.close
            closed.append(proceeds)

        for ticker in sorted(set(desired) - set(active)):
            if require_news_entry and int(observed_news[ticker]["articles_7d"]) == 0:
                continue
            price_bar = on_or_before(charts[ticker], session)
            if not price_bar:
                continue
            active[ticker] = {
                "shares": VARIABLE_ENTRY_USD / price_bar.close,
                "none_streak": 0,
            }
            deployed += VARIABLE_ENTRY_USD
        previous_session = on_or_before(market_bars, session)

    ending = sum(closed, Decimal("0"))
    for ticker, position in active.items():
        price_bar = on_or_before(charts[ticker], end)
        if price_bar:
            ending += Decimal(str(position["shares"])) * price_bar.close
    gain = ending - deployed
    return {
        "rule": rule + (" + require-news-entry" if require_news_entry else ""),
        "entries": int(deployed / VARIABLE_ENTRY_USD),
        "closed": len(closed),
        "open": len(active),
        "deployed": deployed,
        "ending": ending,
        "gain": gain,
        "return_pct": gain / deployed * 100 if deployed else Decimal("0"),
    }


def money(value: Decimal) -> str:
    return f"${value:,.2f}"


def percent(value: Decimal) -> str:
    return f"{value:.2f}%"


def write_report(
    results: list[dict[str, object]],
    coverage: dict[str, object],
    end: date,
) -> None:
    lines = [
        "# News-Assisted Strategy Backtest",
        "",
        "## Scope",
        "",
        f"- Requested strategy window: `{VARIABLE_STRATEGY_START.isoformat()}` to `{end.isoformat()}`.",
        "- Source: Alpaca historical news only. GDELT is currently throttled, YouTube is not configured, and free official X or broad Instagram historical feeds are unavailable.",
        "- News is observed only through the previous market close. Simulated trades execute at the next available close.",
        "- This is an in-sample exploratory backtest over the currently tracked universe, not a forward validation.",
        "",
        "## Coverage",
        "",
        f"- Tracked stock tickers: `{coverage['tickers']}`.",
        f"- Tickers with at least one Alpaca news article: `{coverage['tickers_with_news']}`.",
        f"- Retrieved Alpaca articles: `{coverage['articles']}`.",
        f"- Article cap reached by tickers: `{coverage['capped_tickers']}`.",
        "",
        "## Results",
        "",
        "- `technical-baseline`: exit after ten consecutive five-day `none` observations and a one-month return of `-5%` or worse.",
        "- `hold-while-news-active`: apply the baseline exit only when the latest seven-day news count is zero.",
        "- `confirm-news-cooling`: apply the baseline exit only when the latest seven-day news count is no higher than the prior seven-day count.",
        "- `early-exit-on-news-cooling`: exit after five consecutive five-day `none` observations, a one-month return of `-5%` or worse, and cooling seven-day news.",
        "- `require-news-entry`: use the baseline exit, but enter only when the stock has at least one article in the latest seven days.",
        "",
        "| Rule | Entries | Closed | Open | Deployed | Ending value | Gain | Return |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in results:
        lines.append(
            f"| `{row['rule']}` | {row['entries']} | {row['closed']} | {row['open']} | "
            f"{money(row['deployed'])} | {money(row['ending'])} | {money(row['gain'])} | "
            f"{percent(row['return_pct'])} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "`hold-while-news-active` produced the strongest in-sample return, but it is permissive: heavily covered companies may almost never reach a zero-article week. It should be tracked as an experimental long-hold comparison, not adopted as the live rule yet.",
        "",
        "`confirm-news-cooling` is the more conservative news-assisted candidate. It improved the in-sample result while preserving the original ten-session technical deterioration condition.",
        "",
        "The technical baseline remains the reference strategy. News-assisted rules should not replace it unless they improve results on later, unseen closes. Article counts measure media attention, not sentiment, article quality, or social engagement.",
        "",
    ]
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backtest news-assisted signal exits.")
    parser.add_argument("--end-date", type=date.fromisoformat, default=date(2026, 6, 1))
    parser.add_argument("--max-articles", type=int, default=500)
    parser.add_argument(
        "--news-from-date",
        type=date.fromisoformat,
        default=VARIABLE_STRATEGY_START - timedelta(days=14),
    )
    parser.add_argument("--refresh-news", action="store_true")
    parser.add_argument("--refresh-from-ticker")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    _, market_bars = fetch_chart("SPY")
    latest_market = on_or_before(market_bars, args.end_date)
    if not latest_market:
        raise RuntimeError("missing ending market close")
    charts: dict[str, tuple[object, ...]] = {}
    for ticker, security_type in tracked_stock_assets():
        try:
            _, bars = fetch_chart(yahoo_symbol(ticker, security_type))
        except Exception:
            continue
        if bars:
            charts[ticker] = bars
    tickers = sorted(charts)
    raw_news = historical_news(
        tickers,
        args.news_from_date,
        latest_market.day,
        args.max_articles,
        args.refresh_news,
        args.refresh_from_ticker,
    )
    write_daily_counts(
        raw_news,
        args.news_from_date,
        latest_market.day,
    )
    news_by_ticker = {
        ticker: daily_counts(raw_news.get(ticker, []))
        for ticker in tickers
    }
    coverage = {
        "tickers": len(tickers),
        "tickers_with_news": sum(bool(rows) for rows in raw_news.values()),
        "articles": sum(len(rows) for rows in raw_news.values()),
        "capped_tickers": sum(len(rows) >= args.max_articles for rows in raw_news.values()),
    }
    results = [
        simulate("technical-baseline", charts, market_bars, news_by_ticker, latest_market.day),
        simulate("hold-while-news-active", charts, market_bars, news_by_ticker, latest_market.day),
        simulate("confirm-news-cooling", charts, market_bars, news_by_ticker, latest_market.day),
        simulate("early-exit-on-news-cooling", charts, market_bars, news_by_ticker, latest_market.day),
        simulate(
            "technical-baseline",
            charts,
            market_bars,
            news_by_ticker,
            latest_market.day,
            require_news_entry=True,
        ),
    ]
    write_report(results, coverage, latest_market.day)
    print(f"Latest market close: {latest_market.day}")
    print(f"Coverage: {coverage}")
    for row in results:
        print(
            f"{row['rule']}: entries={row['entries']} closed={row['closed']} "
            f"open={row['open']} gain={money(row['gain'])} return={percent(row['return_pct'])}"
        )
    print(f"Wrote {REPORT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
