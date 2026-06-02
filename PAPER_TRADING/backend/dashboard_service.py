from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from backend.news_strategy import NEWS_STRATEGIES, load_daily_news_counts, news_metrics, should_exit as news_should_exit


ROOT = Path(__file__).resolve().parents[1]
TRADES_FILE = ROOT / "data" / "trades.csv"
DEFAULT_START = date(2026, 5, 20)
HISTORY_START = date(2026, 1, 1)
FETCH_START = date(2025, 12, 1)
TSX_SYMBOLS = {
    "ATD": "ATD.TO",
    "BNS": "BNS.TO",
    "CCO": "CCO.TO",
    "COSY": "COSY.TO",
    "CP": "CP.TO",
    "CU": "CU.TO",
    "ENB": "ENB.TO",
    "FNV": "FNV.TO",
    "FTS": "FTS.TO",
    "HUTL": "HUTL.TO",
    "KITS": "KITS.TO",
    "L": "L.TO",
    "MFC": "MFC.TO",
    "PZA": "PZA.TO",
    "QQC.F": "QQC-F.TO",
    "RY": "RY.TO",
    "SOBO": "SOBO.TO",
    "T": "T.TO",
    "TD": "TD.TO",
    "TOI": "TOI.V",
    "TRP": "TRP.TO",
    "VCN": "VCN.TO",
    "VDY": "VDY.TO",
    "VFV": "VFV.TO",
    "VGRO": "VGRO.TO",
    "XEC": "XEC.TO",
    "XEF": "XEF.TO",
    "XIU": "XIU.TO",
    "ZEQT": "ZEQT.TO",
    "ZGLD": "ZGLD.TO",
    "ZMMK": "ZMMK.TO",
    "ZQQ": "ZQQ.TO",
    "ZSP": "ZSP.TO",
}
CRYPTO_SYMBOLS = {
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
    "USDCUSD": "USDC-USD",
}
PUBLIC_DASHBOARD = os.environ.get("PUBLIC_DASHBOARD", "").casefold() in {
    "1",
    "true",
    "yes",
}
VARIABLE_STRATEGY_NAME = "watchlist-variable"
VARIABLE_BUY_ONLY_NAME = "watchlist-variable-buy-only"
VARIABLE_MORE_SIGNALS_NAME = "watchlist-variable-more-signals"
VARIABLE_STRATEGY_START = date(2026, 1, 31)
VARIABLE_ENTRY_USD = Decimal("1000")


@dataclass(frozen=True)
class Bar:
    day: date
    close: Decimal
    volume: Decimal


def as_float(value: Decimal) -> float:
    return round(float(value), 6)


def pct_change(value: Decimal, baseline: Decimal) -> Decimal:
    if not baseline:
        return Decimal("0")
    return (value / baseline - 1) * 100


def parse_date(value: str | None, fallback: date | None = None) -> date | None:
    return date.fromisoformat(value) if value else fallback


def yahoo_symbol(ticker: str, security_type: str) -> str:
    if security_type == "crypto":
        return CRYPTO_SYMBOLS.get(ticker, ticker)
    return TSX_SYMBOLS.get(ticker, ticker)


@lru_cache(maxsize=512)
def fetch_chart(symbol: str) -> tuple[str, tuple[Bar, ...]]:
    period1 = int(datetime.combine(FETCH_START, datetime.min.time(), tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.now(timezone.utc).timestamp()) + 86_400
    query = urlencode({"period1": period1, "period2": period2, "interval": "1d"})
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?{query}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        result = json.load(response)["chart"]["result"][0]
    quote_rows = result["indicators"]["quote"][0]
    closes = quote_rows["close"]
    volumes = quote_rows.get("volume", [0] * len(closes))
    bars = tuple(
        Bar(
            datetime.fromtimestamp(timestamp, timezone.utc).date(),
            Decimal(str(close)),
            Decimal(str(volume or 0)),
        )
        for timestamp, close, volume in zip(result["timestamp"], closes, volumes)
        if close is not None
    )
    return result["meta"]["currency"], bars


def on_or_after(bars: tuple[Bar, ...], day: date) -> Bar | None:
    return next((bar for bar in bars if bar.day >= day), None)


def on_or_before(bars: tuple[Bar, ...], day: date | None) -> Bar | None:
    if day is None:
        return bars[-1] if bars else None
    return next((bar for bar in reversed(bars) if bar.day <= day), None)


def read_trades() -> list[dict[str, str]]:
    with TRADES_FILE.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def allocations() -> dict[str, dict[tuple[str, str], Decimal]]:
    grouped: dict[str, dict[tuple[str, str], Decimal]] = defaultdict(
        lambda: defaultdict(lambda: Decimal("0"))
    )
    for trade in read_trades():
        amount = Decimal(trade["usd_amount"])
        direction = Decimal("1") if trade["side"] == "buy" else Decimal("-1")
        grouped[trade["investor"]][(trade["ticker"], trade["security_type"])] += (
            amount * direction
        )
    return grouped


def owners_by_asset() -> dict[tuple[str, str], list[str]]:
    owners: dict[tuple[str, str], set[str]] = defaultdict(set)
    for investor, assets in allocations().items():
        for asset, amount in assets.items():
            if amount:
                owners[asset].add(investor)
    return {asset: sorted(names) for asset, names in owners.items()}


def tracked_stock_assets() -> list[tuple[str, str]]:
    return sorted(
        {
            (trade["ticker"], trade["security_type"])
            for trade in read_trades()
            if trade["security_type"] == "stock"
        }
    )


SIGNAL_HORIZONS = (
    ("3d", "3 days", 3, None, Decimal("5")),
    ("5d", "5 days", 5, None, Decimal("10")),
    ("1w", "1 week", None, 7, Decimal("10")),
    ("1m", "1 month", 21, None, Decimal("20")),
    ("3m", "3 months", 63, None, Decimal("30")),
)
COMPOSITE_WEIGHTS = {
    "3d": Decimal("0.20"),
    "5d": Decimal("0.30"),
    "1w": Decimal("0.25"),
    "1m": Decimal("0.25"),
}


def clamp(value: Decimal, minimum: Decimal = Decimal("0"), maximum: Decimal = Decimal("100")) -> Decimal:
    return max(minimum, min(maximum, value))


def horizon_signal(
    bars: tuple[Bar, ...],
    key: str,
    label: str,
    sessions: int | None,
    calendar_days: int | None,
    momentum_threshold: Decimal,
) -> dict[str, object] | None:
    if len(bars) < 22:
        return None
    current = bars[-1]
    if calendar_days:
        cutoff = current.day - timedelta(days=calendar_days)
        start_index = next(
            (index for index, bar in enumerate(bars) if bar.day >= cutoff),
            len(bars) - 1,
        )
        start_index = min(start_index, len(bars) - 2)
    else:
        if sessions is None or len(bars) <= sessions:
            return None
        start_index = len(bars) - sessions - 1
    horizon_bars = bars[start_index + 1 :]
    baseline = bars[start_index]
    normal_start = max(0, start_index - 20)
    normal_bars = bars[normal_start:start_index]
    if not normal_bars or not horizon_bars:
        return None
    normal_volume = sum((bar.volume for bar in normal_bars), Decimal("0")) / len(normal_bars)
    if not normal_volume:
        return None
    volume_ratio = sum((bar.volume for bar in horizon_bars), Decimal("0")) / len(horizon_bars) / normal_volume
    return_pct = pct_change(current.close, baseline.close)
    recent_high_bars = bars[max(0, len(bars) - max(21, len(horizon_bars) + 1)) : -1]
    distance = pct_change(current.close, max(bar.close for bar in recent_high_bars))
    momentum_score = clamp(return_pct / momentum_threshold * 100)
    volume_score = clamp((volume_ratio - 1) / Decimal("0.5") * 100)
    high_score = clamp((distance + 10) / 10 * 100)
    score = momentum_score * Decimal("0.40") + volume_score * Decimal("0.40") + high_score * Decimal("0.20")
    strict = return_pct >= momentum_threshold and volume_ratio >= Decimal("1.5") and distance >= -2
    near = volume_ratio >= Decimal("1.25") and distance >= -2
    return {
        "key": key,
        "label": label,
        "start_date": baseline.day.isoformat(),
        "as_of": current.day.isoformat(),
        "return_pct": as_float(return_pct),
        "volume_ratio": as_float(volume_ratio),
        "distance_to_20d_high_pct": as_float(distance),
        "score": as_float(score),
        "classification": "strict" if strict else ("near" if near else "none"),
        "fresh_priority": bool(strict and return_pct <= momentum_threshold * Decimal("2.5")),
    }


def live_signal(bars: tuple[Bar, ...]) -> dict[str, object] | None:
    horizons = {
        key: signal
        for key, label, sessions, calendar_days, threshold in SIGNAL_HORIZONS
        if (
            signal := horizon_signal(
                bars, key, label, sessions, calendar_days, threshold
            )
        )
    }
    if "5d" not in horizons:
        return None
    weighted_score = sum(
        (Decimal(str(horizons[key]["score"])) * weight for key, weight in COMPOSITE_WEIGHTS.items() if key in horizons),
        Decimal("0"),
    )
    applied_weight = sum((weight for key, weight in COMPOSITE_WEIGHTS.items() if key in horizons), Decimal("0"))
    weighted_score = weighted_score / applied_weight if applied_weight else Decimal("0")
    overall_classification = "strict" if weighted_score >= 70 else ("near" if weighted_score >= 45 else "none")
    five_day = horizons["5d"]
    return {
        "as_of": five_day["as_of"],
        "five_day_return_pct": five_day["return_pct"],
        "five_day_volume_ratio": five_day["volume_ratio"],
        "distance_to_20d_high_pct": five_day["distance_to_20d_high_pct"],
        "classification": five_day["classification"],
        "fresh_priority": five_day["fresh_priority"],
        "overall_score": as_float(weighted_score),
        "overall_classification": overall_classification,
        "horizons": horizons,
        "composite_weights": {key: as_float(weight) for key, weight in COMPOSITE_WEIGHTS.items()},
    }


def entry_signal(signal: dict[str, object] | None) -> str | None:
    if not signal or signal["classification"] == "none":
        return None
    if signal["fresh_priority"]:
        return "fresh"
    return str(signal["classification"])


def variable_strategy_detail(
    start: date,
    end: date | None,
    strategy_name: str = VARIABLE_STRATEGY_NAME,
    more_signals_exit: bool = False,
    news_rule: str | None = None,
    require_news_entry: bool = False,
) -> dict[str, object]:
    selected_start = max(start, VARIABLE_STRATEGY_START)
    _, market_bars = fetch_chart("SPY")
    latest_market = on_or_before(market_bars, end)
    if not latest_market:
        raise ValueError("missing strategy ending market session")
    sessions = [
        bar.day
        for bar in market_bars
        if VARIABLE_STRATEGY_START <= bar.day <= latest_market.day
    ]
    if not sessions:
        raise ValueError("missing strategy market sessions")

    charts: dict[str, tuple[Bar, ...]] = {}
    for ticker, security_type in tracked_stock_assets():
        symbol = yahoo_symbol(ticker, security_type)
        try:
            _, bars = fetch_chart(symbol)
        except Exception:
            continue
        if bars:
            charts[ticker] = bars

    active: dict[str, dict[str, object]] = {}
    cycles: list[dict[str, object]] = []
    series: list[dict[str, object]] = []
    deployed = Decimal("0")
    realized = Decimal("0")
    previous_session = on_or_before(market_bars, VARIABLE_STRATEGY_START - timedelta(days=1))
    daily_news = load_daily_news_counts()
    news_counts = daily_news.get("tickers", {})
    if not isinstance(news_counts, dict):
        news_counts = {}

    for session in sessions:
        if not previous_session:
            previous_session = on_or_before(market_bars, session - timedelta(days=1))
        desired: dict[str, str] = {}
        observed: dict[str, dict[str, object] | None] = {}
        observed_news: dict[str, dict[str, Decimal | int | None]] = {}
        for ticker, bars in charts.items():
            signal_bars = tuple(bar for bar in bars if bar.day <= previous_session.day)
            observed[ticker] = live_signal(signal_bars)
            ticker_counts = news_counts.get(ticker, {})
            observed_news[ticker] = news_metrics(
                ticker_counts if isinstance(ticker_counts, dict) else {},
                previous_session.day,
            )
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
            position["none_streak"] = int(position.get("none_streak", 0)) + 1
            signal = observed[ticker] or {}
            one_month = signal.get("horizons", {}).get("1m", {})
            one_month_return = Decimal(str(one_month.get("return_pct", "0")))
            if news_rule:
                should_exit = news_should_exit(
                    news_rule,
                    int(position["none_streak"]),
                    one_month_return,
                    observed_news[ticker],
                )
            else:
                should_exit = (
                    position["none_streak"] >= 10 and one_month_return <= Decimal("-5")
                    if more_signals_exit
                    else position["none_streak"] >= 1
                )
            if not should_exit:
                active[ticker] = position
                continue
            proceeds = Decimal(str(position["shares"])) * price_bar.close
            pnl = proceeds - VARIABLE_ENTRY_USD
            realized += pnl
            cycles.append(
                {
                    **position,
                    "exit_date": price_bar.day.isoformat(),
                    "exit_price": as_float(price_bar.close),
                    "ending_value": as_float(proceeds),
                    "gain_loss": as_float(pnl),
                    "return_pct": as_float(pct_change(proceeds, VARIABLE_ENTRY_USD)),
                    "status": "closed",
                }
            )

        for ticker in sorted(set(desired) - set(active)):
            if require_news_entry and int(observed_news[ticker]["articles_7d"]) == 0:
                continue
            price_bar = on_or_before(charts[ticker], session)
            if not price_bar:
                continue
            shares = VARIABLE_ENTRY_USD / price_bar.close
            deployed += VARIABLE_ENTRY_USD
            active[ticker] = {
                "ticker": ticker,
                "entry_signal": desired[ticker],
                "entry_date": price_bar.day.isoformat(),
                "entry_price": as_float(price_bar.close),
                "shares": shares,
                "initial_value": as_float(VARIABLE_ENTRY_USD),
                "none_streak": 0,
            }

        open_value = Decimal("0")
        for ticker, position in active.items():
            price_bar = on_or_before(charts[ticker], session)
            if price_bar:
                open_value += Decimal(str(position["shares"])) * price_bar.close
        series.append(
            {
                "date": session.isoformat(),
                "value": as_float(deployed + realized + open_value - VARIABLE_ENTRY_USD * len(active)),
                "gain_loss": as_float(realized + open_value - VARIABLE_ENTRY_USD * len(active)),
                "deployed_capital": as_float(deployed),
                "active_positions": len(active),
            }
        )
        previous_session = on_or_before(market_bars, session)

    open_positions: list[dict[str, object]] = []
    open_value = Decimal("0")
    for ticker, position in active.items():
        price_bar = on_or_before(charts[ticker], latest_market.day)
        if not price_bar:
            continue
        current_value = Decimal(str(position["shares"])) * price_bar.close
        pnl = current_value - VARIABLE_ENTRY_USD
        open_value += current_value
        open_positions.append(
            {
                **position,
                "current_value": as_float(current_value),
                "gain_loss": as_float(pnl),
                "return_pct": as_float(pct_change(current_value, VARIABLE_ENTRY_USD)),
                "status": "open",
            }
        )

    category_rows: list[dict[str, object]] = []
    for category in ("fresh", "strict", "near"):
        category_cycles = [cycle for cycle in cycles if cycle["entry_signal"] == category]
        category_open = [position for position in open_positions if position["entry_signal"] == category]
        invested = VARIABLE_ENTRY_USD * (len(category_cycles) + len(category_open))
        ending_value = sum(
            (Decimal(str(cycle["ending_value"])) for cycle in category_cycles),
            Decimal("0"),
        ) + sum(
            (Decimal(str(position["current_value"])) for position in category_open),
            Decimal("0"),
        )
        category_rows.append(
            {
                "category": category,
                "entries": len(category_cycles) + len(category_open),
                "closed_positions": len(category_cycles),
                "open_positions": len(category_open),
                "deployed_capital": as_float(invested),
                "ending_value": as_float(ending_value),
                "gain_loss": as_float(ending_value - invested),
                "return_pct": as_float(pct_change(ending_value, invested)),
            }
        )
    category_rows.sort(key=lambda row: row["return_pct"], reverse=True)

    ending_series = series[-1]
    prior_series = next(
        (
            row
            for row in reversed(series)
            if date.fromisoformat(str(row["date"])) < selected_start
        ),
        None,
    )
    starting_equity = Decimal(str(prior_series["value"])) if prior_series else Decimal("0")
    starting_deployed = (
        Decimal(str(prior_series["deployed_capital"])) if prior_series else Decimal("0")
    )
    ending_equity = Decimal(str(ending_series["value"]))
    ending_deployed = Decimal(str(ending_series["deployed_capital"]))
    new_deployments = ending_deployed - starting_deployed
    period_basis = starting_equity + new_deployments
    period_gain = ending_equity - period_basis
    open_positions.sort(key=lambda row: row["return_pct"], reverse=True)
    return {
        "investor": strategy_name,
        "source": (
            "derived-news-assisted-signal-strategy"
            if news_rule or require_news_entry
            else (
                "derived-multi-signal-exit-strategy"
                if more_signals_exit
                else "derived-daily-signal-strategy"
            )
        ),
        "strategy_start": VARIABLE_STRATEGY_START.isoformat(),
        "from_date": selected_start.isoformat(),
        "to_date": latest_market.day.isoformat(),
        "initial_value": as_float(period_basis),
        "current_value": as_float(ending_equity),
        "gain_loss": as_float(period_gain),
        "return_pct": as_float(pct_change(ending_equity, period_basis)),
        "position_count": len(open_positions),
        "positions": open_positions,
        "series": [
            row
            for row in series
            if date.fromisoformat(str(row["date"])) >= selected_start
        ],
        "category_stats": category_rows,
        "category_stats_scope": f"{VARIABLE_STRATEGY_START.isoformat()} to {latest_market.day.isoformat()}",
        "trade_cycles": len(cycles) + len(open_positions),
        "closed_cycles": len(cycles),
        "news_counts_to_date": daily_news.get("to_date") if news_rule or require_news_entry else None,
        "note": (
            f"News-assisted EOD strategy. {NEWS_STRATEGIES[strategy_name]['note']} "
            f"Committed Alpaca daily news counts currently end on {daily_news.get('to_date')}. "
            "Signals and news are observed at one close and executed at the next "
            "available close. Each entry deploys $1,000. FX conversion is intentionally ignored."
            if news_rule or require_news_entry
            else
            "Multi-signal EOD strategy. Entries use the five-day non-none signal. "
            "An exit requires ten consecutive five-day none observations and a "
            "one-month return of -5% or worse. Signals are observed at one close "
            "and executed at the next available close. Each entry deploys $1,000. "
            "FX conversion is intentionally ignored."
            if more_signals_exit
            else
            "Daily EOD signal strategy. Signals are observed at one market close "
            "and executed at the next available close. Each entry deploys $1,000. "
            "FX conversion is intentionally ignored."
        ),
    }


def variable_strategy_summary(start: date, end: date | None) -> dict[str, object]:
    detail = variable_strategy_detail(start, end)
    return {
        key: detail[key]
        for key in (
            "investor",
            "initial_value",
            "current_value",
            "gain_loss",
            "return_pct",
            "position_count",
            "source",
        )
    } | {"warnings": []}


def variable_more_signals_summary(start: date, end: date | None) -> dict[str, object]:
    detail = variable_strategy_detail(
        start,
        end,
        strategy_name=VARIABLE_MORE_SIGNALS_NAME,
        more_signals_exit=True,
    )
    return {
        key: detail[key]
        for key in (
            "investor",
            "initial_value",
            "current_value",
            "gain_loss",
            "return_pct",
            "position_count",
            "source",
        )
    } | {"warnings": []}


def variable_news_strategy_summary(
    strategy_name: str,
    start: date,
    end: date | None,
) -> dict[str, object]:
    config = NEWS_STRATEGIES[strategy_name]
    detail = variable_strategy_detail(
        start,
        end,
        strategy_name=strategy_name,
        news_rule=str(config["rule"]),
        require_news_entry=bool(config["require_news_entry"]),
    )
    return {
        key: detail[key]
        for key in (
            "investor",
            "initial_value",
            "current_value",
            "gain_loss",
            "return_pct",
            "position_count",
            "source",
        )
    } | {"warnings": []}


def variable_buy_only_detail(start: date, end: date | None) -> dict[str, object]:
    selected_start = max(start, VARIABLE_STRATEGY_START)
    _, market_bars = fetch_chart("SPY")
    latest_market = on_or_before(market_bars, end)
    if not latest_market:
        raise ValueError("missing strategy ending market session")
    sessions = [
        bar.day
        for bar in market_bars
        if VARIABLE_STRATEGY_START <= bar.day <= latest_market.day
    ]
    if not sessions:
        raise ValueError("missing strategy market sessions")

    charts: dict[str, tuple[Bar, ...]] = {}
    for ticker, security_type in tracked_stock_assets():
        symbol = yahoo_symbol(ticker, security_type)
        try:
            _, bars = fetch_chart(symbol)
        except Exception:
            continue
        if bars:
            charts[ticker] = bars

    positions: dict[str, dict[str, object]] = {}
    series: list[dict[str, object]] = []
    previous_session = on_or_before(market_bars, VARIABLE_STRATEGY_START - timedelta(days=1))
    for session in sessions:
        if not previous_session:
            previous_session = on_or_before(market_bars, session - timedelta(days=1))
        for ticker, bars in charts.items():
            if ticker in positions:
                continue
            signal_bars = tuple(bar for bar in bars if bar.day <= previous_session.day)
            category = entry_signal(live_signal(signal_bars))
            if not category:
                continue
            price_bar = on_or_before(bars, session)
            if not price_bar:
                continue
            positions[ticker] = {
                "ticker": ticker,
                "entry_signal": category,
                "entry_date": price_bar.day.isoformat(),
                "entry_price": as_float(price_bar.close),
                "shares": VARIABLE_ENTRY_USD / price_bar.close,
                "initial_value": as_float(VARIABLE_ENTRY_USD),
            }
        deployed = VARIABLE_ENTRY_USD * len(positions)
        current = Decimal("0")
        for ticker, position in positions.items():
            price_bar = on_or_before(charts[ticker], session)
            if price_bar:
                current += Decimal(str(position["shares"])) * price_bar.close
        series.append(
            {
                "date": session.isoformat(),
                "value": as_float(current),
                "gain_loss": as_float(current - deployed),
                "deployed_capital": as_float(deployed),
                "active_positions": len(positions),
            }
        )
        previous_session = on_or_before(market_bars, session)

    open_positions: list[dict[str, object]] = []
    for ticker, position in positions.items():
        price_bar = on_or_before(charts[ticker], latest_market.day)
        if not price_bar:
            continue
        current_value = Decimal(str(position["shares"])) * price_bar.close
        open_positions.append(
            {
                **position,
                "current_value": as_float(current_value),
                "gain_loss": as_float(current_value - VARIABLE_ENTRY_USD),
                "return_pct": as_float(pct_change(current_value, VARIABLE_ENTRY_USD)),
                "status": "open",
            }
        )

    category_rows: list[dict[str, object]] = []
    for category in ("fresh", "strict", "near"):
        category_positions = [
            position for position in open_positions if position["entry_signal"] == category
        ]
        invested = VARIABLE_ENTRY_USD * len(category_positions)
        ending_value = sum(
            (Decimal(str(position["current_value"])) for position in category_positions),
            Decimal("0"),
        )
        category_rows.append(
            {
                "category": category,
                "entries": len(category_positions),
                "closed_positions": 0,
                "open_positions": len(category_positions),
                "deployed_capital": as_float(invested),
                "ending_value": as_float(ending_value),
                "gain_loss": as_float(ending_value - invested),
                "return_pct": as_float(pct_change(ending_value, invested)),
            }
        )
    category_rows.sort(key=lambda row: row["return_pct"], reverse=True)

    ending_series = series[-1]
    prior_series = next(
        (
            row
            for row in reversed(series)
            if date.fromisoformat(str(row["date"])) < selected_start
        ),
        None,
    )
    starting_equity = Decimal(str(prior_series["value"])) if prior_series else Decimal("0")
    starting_deployed = (
        Decimal(str(prior_series["deployed_capital"])) if prior_series else Decimal("0")
    )
    ending_equity = Decimal(str(ending_series["value"]))
    ending_deployed = Decimal(str(ending_series["deployed_capital"]))
    new_deployments = ending_deployed - starting_deployed
    period_basis = starting_equity + new_deployments
    period_gain = ending_equity - period_basis
    open_positions.sort(key=lambda row: row["return_pct"], reverse=True)
    return {
        "investor": VARIABLE_BUY_ONLY_NAME,
        "source": "derived-buy-only-signal-strategy",
        "strategy_start": VARIABLE_STRATEGY_START.isoformat(),
        "from_date": selected_start.isoformat(),
        "to_date": latest_market.day.isoformat(),
        "initial_value": as_float(period_basis),
        "current_value": as_float(ending_equity),
        "gain_loss": as_float(period_gain),
        "return_pct": as_float(pct_change(ending_equity, period_basis)),
        "position_count": len(open_positions),
        "positions": open_positions,
        "series": [
            row
            for row in series
            if date.fromisoformat(str(row["date"])) >= selected_start
        ],
        "category_stats": category_rows,
        "category_stats_scope": f"{VARIABLE_STRATEGY_START.isoformat()} to {latest_market.day.isoformat()}",
        "trade_cycles": len(open_positions),
        "closed_cycles": 0,
        "note": (
            "Buy-only EOD signal strategy. A stock is purchased once, at the next "
            "available close after its first non-none signal, and is never sold. "
            "Each entry deploys $1,000. FX conversion is intentionally ignored."
        ),
    }


def variable_buy_only_summary(start: date, end: date | None) -> dict[str, object]:
    detail = variable_buy_only_detail(start, end)
    return {
        key: detail[key]
        for key in (
            "investor",
            "initial_value",
            "current_value",
            "gain_loss",
            "return_pct",
            "position_count",
            "source",
        )
    } | {"warnings": []}


def asset_summary(
    asset: tuple[str, str],
    owners: list[str],
    start: date,
    end: date | None,
) -> dict[str, object]:
    ticker, security_type = asset
    symbol = yahoo_symbol(ticker, security_type)
    try:
        currency, bars = fetch_chart(symbol)
        baseline = on_or_after(bars, start)
        latest = on_or_before(bars, end)
        if not baseline or not latest or baseline.day > latest.day:
            raise ValueError("missing prices for selected window")
        signal_bars = tuple(bar for bar in bars if bar.day <= latest.day)
        return {
            "ticker": ticker,
            "security_type": security_type,
            "yahoo_symbol": symbol,
            "owners": owners,
            "currency": currency,
            "start_date": baseline.day.isoformat(),
            "end_date": latest.day.isoformat(),
            "start_price": as_float(baseline.close),
            "end_price": as_float(latest.close),
            "return_pct": as_float(pct_change(latest.close, baseline.close)),
            "signal": live_signal(signal_bars),
            "warning": None,
        }
    except Exception as exc:
        return {
            "ticker": ticker,
            "security_type": security_type,
            "yahoo_symbol": symbol,
            "owners": owners,
            "warning": str(exc),
            "signal": None,
        }


def all_asset_summaries(start: date, end: date | None) -> list[dict[str, object]]:
    owners = owners_by_asset()
    rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=24) as executor:
        futures = {
            executor.submit(asset_summary, asset, names, start, end): asset
            for asset, names in owners.items()
        }
        for future in as_completed(futures):
            rows.append(future.result())
    return sorted(rows, key=lambda row: row["ticker"])


def nisarg_summary(start: date, end: date | None) -> dict[str, object] | None:
    if PUBLIC_DASHBOARD:
        return None
    try:
        from nisarg_window_return import calculate_window

        result = calculate_window(start, end)
        return {
            "investor": "nisarg",
            "initial_value": as_float(result.deployed_capital_usd),
            "current_value": as_float(result.ending_proceeds_and_value_usd),
            "gain_loss": as_float(result.gain_usd),
            "return_pct": as_float(result.return_pct),
            "position_count": len(result.details),
            "source": "wealthsimple-import",
            "warnings": result.warnings,
        }
    except Exception as exc:
        return {
            "investor": "nisarg",
            "initial_value": 0,
            "current_value": 0,
            "gain_loss": 0,
            "return_pct": 0,
            "position_count": 0,
            "source": "wealthsimple-import",
            "warnings": [str(exc)],
        }


def build_overview(start: date, end: date | None) -> dict[str, object]:
    grouped = allocations()
    stocks = all_asset_summaries(start, end)
    indexed = {(row["ticker"], row["security_type"]): row for row in stocks}
    fx_currency, fx_bars = fetch_chart("CAD=X")
    if fx_currency != "CAD":
        raise ValueError("unexpected CAD=X currency")
    traders: list[dict[str, object]] = []
    for investor, assets in grouped.items():
        initial = Decimal("0")
        current = Decimal("0")
        warnings: list[str] = []
        for asset, amount in assets.items():
            if not amount:
                continue
            initial += amount
            row = indexed[asset]
            if row.get("warning"):
                current += amount
                warnings.append(f"{asset[0]}: {row['warning']}")
            else:
                growth = Decimal(str(row["end_price"])) / Decimal(str(row["start_price"]))
                if row["currency"] == "CAD":
                    start_fx = on_or_after(fx_bars, date.fromisoformat(row["start_date"]))
                    end_fx = on_or_before(fx_bars, date.fromisoformat(row["end_date"]))
                    if not start_fx or not end_fx:
                        raise ValueError("missing CAD/USD exchange rate")
                    growth *= start_fx.close / end_fx.close
                current += amount * growth
        gain = current - initial
        traders.append(
            {
                "investor": investor,
                "initial_value": as_float(initial),
                "current_value": as_float(current),
                "gain_loss": as_float(gain),
                "return_pct": as_float(pct_change(current, initial)),
                "position_count": sum(bool(amount) for amount in assets.values()),
                "source": "paper-ledger",
                "warnings": warnings,
            }
        )
    imported = nisarg_summary(start, end)
    if imported:
        traders.append(imported)
    traders.append(variable_strategy_summary(start, end))
    traders.append(variable_buy_only_summary(start, end))
    traders.append(variable_more_signals_summary(start, end))
    for strategy_name in NEWS_STRATEGIES:
        traders.append(variable_news_strategy_summary(strategy_name, start, end))
    traders.sort(key=lambda row: row["return_pct"], reverse=True)
    for rank, trader in enumerate(traders, start=1):
        trader["rank"] = rank
    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat() if end else None,
        "latest_available_date": max(
            (row.get("end_date", "") for row in stocks if not row.get("warning")),
            default="",
        ),
        "traders": traders,
        "stocks": stocks,
    }


def build_eod_snapshot() -> dict[str, object]:
    _, market_bars = fetch_chart("SPY")
    if len(market_bars) < 2:
        raise ValueError("missing market sessions for EOD snapshot")
    previous, latest = market_bars[-2:]
    overview = build_overview(previous.day, latest.day)
    stocks = sorted(
        (row for row in overview["stocks"] if not row.get("warning")),
        key=lambda row: row["return_pct"],
        reverse=True,
    )
    return {
        "from_date": previous.day.isoformat(),
        "to_date": latest.day.isoformat(),
        "traders": overview["traders"],
        "stocks": stocks,
    }


def latest_market_date() -> date:
    _, market_bars = fetch_chart("SPY")
    if not market_bars:
        raise ValueError("missing market sessions")
    return market_bars[-1].day


def asset_detail(ticker: str, start: date, end: date | None) -> dict[str, object]:
    matches = [
        (asset, names)
        for asset, names in owners_by_asset().items()
        if asset[0].casefold() == ticker.casefold()
    ]
    if not matches:
        raise KeyError(ticker)
    asset, owners = matches[0]
    summary = asset_summary(asset, owners, start, end)
    if summary.get("warning"):
        return {**summary, "series": []}
    _, bars = fetch_chart(summary["yahoo_symbol"])
    series = [
        {"date": bar.day.isoformat(), "price": as_float(bar.close), "volume": as_float(bar.volume)}
        for bar in bars
        if bar.day >= start and (end is None or bar.day <= end)
    ]
    return {**summary, "series": series}


def paper_trader_detail(investor: str, start: date, end: date | None) -> dict[str, object]:
    grouped = allocations()
    matched = next((name for name in grouped if name.casefold() == investor.casefold()), None)
    if not matched:
        raise KeyError(investor)
    assets = grouped[matched]
    fx_currency, fx_bars = fetch_chart("CAD=X")
    if fx_currency != "CAD":
        raise ValueError("unexpected CAD=X currency")
    latest_fx = on_or_before(fx_bars, end)
    if not latest_fx:
        raise ValueError("missing CAD/USD exchange rate")
    positions: list[dict[str, object]] = []
    daily_parts: list[tuple[Decimal, str, tuple[Bar, ...], Decimal]] = []
    for (ticker, security_type), amount in assets.items():
        if not amount:
            continue
        symbol = yahoo_symbol(ticker, security_type)
        try:
            currency, bars = fetch_chart(symbol)
            baseline = on_or_after(bars, start)
            latest = on_or_before(bars, end)
            if not baseline or not latest:
                raise ValueError("missing prices for selected window")
            baseline_fx = on_or_after(fx_bars, baseline.day)
            if currency == "CAD":
                if not baseline_fx:
                    raise ValueError("missing inception CAD/USD exchange rate")
                quantity = amount * baseline_fx.close / baseline.close
                current = quantity * latest.close / latest_fx.close
            elif currency == "USD":
                quantity = amount / baseline.close
                current = quantity * latest.close
            else:
                raise ValueError(f"unsupported currency {currency}")
            daily_parts.append((quantity, currency, bars, amount))
            positions.append(
                {
                    "ticker": ticker,
                    "security_type": security_type,
                    "initial_value": as_float(amount),
                    "current_value": as_float(current),
                    "gain_loss": as_float(current - amount),
                    "return_pct": as_float(pct_change(current, amount)),
                    "warning": None,
                }
            )
        except Exception as exc:
            positions.append(
                {
                    "ticker": ticker,
                    "security_type": security_type,
                    "initial_value": as_float(amount),
                    "current_value": as_float(amount),
                    "gain_loss": 0,
                    "return_pct": 0,
                    "warning": str(exc),
                }
            )
    series_days = sorted(
        {
            bar.day
            for _, _, bars, _ in daily_parts
            for bar in bars
            if bar.day >= start and (end is None or bar.day <= end)
        }
    )
    series = []
    for day in series_days:
        fx = on_or_before(fx_bars, day)
        total = Decimal("0")
        if not fx:
            continue
        for quantity, currency, bars, _ in daily_parts:
            bar = on_or_before(bars, day)
            if not bar:
                continue
            total += quantity * bar.close / fx.close if currency == "CAD" else quantity * bar.close
        series.append({"date": day.isoformat(), "value": as_float(total)})
    initial = sum((Decimal(str(row["initial_value"])) for row in positions), Decimal("0"))
    current = sum((Decimal(str(row["current_value"])) for row in positions), Decimal("0"))
    positions.sort(key=lambda row: row["return_pct"], reverse=True)
    return {
        "investor": matched,
        "source": "paper-ledger",
        "initial_value": as_float(initial),
        "current_value": as_float(current),
        "gain_loss": as_float(current - initial),
        "return_pct": as_float(pct_change(current, initial)),
        "positions": positions,
        "series": series,
    }


def nisarg_detail(start: date, end: date | None) -> dict[str, object]:
    from nisarg_window_return import calculate_window

    result = calculate_window(start, end)
    positions = [
        {
            "ticker": detail.ticker,
            "initial_value": as_float(detail.opening_value_usd),
            "current_value": as_float(detail.ending_value_usd),
            "gain_loss": as_float(detail.ending_value_usd - detail.opening_value_usd),
            "opening_quantity": as_float(detail.opening_quantity),
            "ending_quantity": as_float(detail.ending_quantity),
        }
        for detail in result.details
    ]
    positions.sort(key=lambda row: abs(row["gain_loss"]), reverse=True)
    return {
        "investor": "nisarg",
        "source": "wealthsimple-import",
        "initial_value": as_float(result.deployed_capital_usd),
        "current_value": as_float(result.ending_proceeds_and_value_usd),
        "gain_loss": as_float(result.gain_usd),
        "return_pct": as_float(result.return_pct),
        "positions": positions,
        "series": [],
        "warnings": result.warnings,
        "note": "Deposits, withdrawals, dividends, fees, interest, and FX cash movements are excluded.",
    }


def trader_detail(investor: str, start: date, end: date | None) -> dict[str, object]:
    news_strategy = NEWS_STRATEGIES.get(investor.casefold())
    if news_strategy:
        return variable_strategy_detail(
            start,
            end,
            strategy_name=investor.casefold(),
            news_rule=str(news_strategy["rule"]),
            require_news_entry=bool(news_strategy["require_news_entry"]),
        )
    if investor.casefold() == VARIABLE_MORE_SIGNALS_NAME:
        return variable_strategy_detail(
            start,
            end,
            strategy_name=VARIABLE_MORE_SIGNALS_NAME,
            more_signals_exit=True,
        )
    if investor.casefold() == VARIABLE_BUY_ONLY_NAME:
        return variable_buy_only_detail(start, end)
    if investor.casefold() == VARIABLE_STRATEGY_NAME:
        return variable_strategy_detail(start, end)
    if investor.casefold() == "nisarg":
        if PUBLIC_DASHBOARD:
            raise KeyError(investor)
        return nisarg_detail(start, end)
    return paper_trader_detail(investor, start, end)
