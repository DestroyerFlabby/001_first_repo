from __future__ import annotations

import csv
import json
import math
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
from backend.wealthsimple_metadata import WEALTHSIMPLE_FX_FEE_RATE, wealthsimple_metadata


ROOT = Path(__file__).resolve().parents[1]
TRADES_FILE = ROOT / "data" / "trades.csv"
MASS_CHANGE_WATCHLIST_FILE = ROOT / "data" / "mass_change_watchlist.csv"
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
MASS_CHANGE_STRATEGY_NAME = "watchlist-variable-mass-change"
HYBRID_NEWS_OPTIMIZED_STRATEGY_NAME = "watchlist-variable-news-optimized-hybrid"
ANALYSIS_DRIVEN_STRATEGY_NAME = "watchlist-variable-news-analysis-driven"
MASTER_STRATEGY_NAME = "watchlist-master"
VARIABLE_BUY_ONLY_NAME = "watchlist-variable-buy-only"
VARIABLE_BUY_ONLY_STRATEGIES = {
    "watchlist-variable-buy-only-fresh-only": "fresh",
    "watchlist-variable-buy-only-strict-only": "strict",
    "watchlist-variable-buy-only-near-only": "near",
}
VARIABLE_MORE_SIGNALS_NAME = "watchlist-variable-more-signals"
ANALYSIS_ENTRY_SCORE = Decimal("180")
VARIABLE_TECHNICAL_STRATEGIES = {
    "watchlist-variable-fresh-only": {
        "entry_categories": {"fresh"},
    },
    "watchlist-variable-strict-only": {
        "entry_categories": {"strict"},
    },
    "watchlist-variable-near-only": {
        "entry_categories": {"near"},
    },
    "watchlist-variable-more-signals-fresh-only": {
        "entry_categories": {"fresh"},
        "more_signals_exit": True,
    },
    "watchlist-variable-more-signals-strict-only": {
        "entry_categories": {"strict"},
        "more_signals_exit": True,
    },
    "watchlist-variable-more-signals-near-only": {
        "entry_categories": {"near"},
        "more_signals_exit": True,
    },
}
SECTOR_OWNER_LABELS = {
    "advanced-packaging": "Semiconductors - Advanced Packaging",
    "chip_design": "Semiconductors - Chip Design",
    "cmp-cleaning-metrology": "Semiconductors - CMP, Cleaning & Metrology",
    "deposition-etch": "Semiconductors - Deposition & Etch",
    "leading-edge-logic-foundry": "Semiconductors - Leading-Edge Foundry",
    "lithography": "Semiconductors - Lithography",
    "memory": "Semiconductors - Memory",
    "photomasks-eda": "Semiconductors - Photomasks & EDA",
    "raw-materials-specialty-gases": "Semiconductors - Materials & Gases",
    "silicon-wafers": "Semiconductors - Silicon Wafers",
    "short-term-watchlist": "Tactical Momentum",
    "long-term-watchlist": "Long-Term Watchlist",
    "insta_watchlist": "Creator / Social Watchlist",
    "daily-watchlist-2026-06-01": "Daily Fresh Setups",
    "analyst-nathan-jones": "Analyst Picks - Industrials",
    "analyst-patrick-brown": "Analyst Picks - Freight & Materials",
    "analyst-chris-dendrinos": "Analyst Picks - Clean Tech",
    "analyst-mike-mayo": "Analyst Picks - Financials",
    MASS_CHANGE_STRATEGY_NAME: "News-Driven Mass Change",
    HYBRID_NEWS_OPTIMIZED_STRATEGY_NAME: "Hybrid News-Optimized",
    ANALYSIS_DRIVEN_STRATEGY_NAME: "News + Analysis Driven",
    MASTER_STRATEGY_NAME: "Master Ranked Portfolio",
}
TICKER_SECTOR_OVERRIDES = {
    "AAOI": "Optical & Networking",
    "AAPL": "Consumer Technology",
    "ADBE": "Software",
    "AIQ": "ETF / Thematic AI",
    "AMD": "Semiconductors - Chip Design",
    "AMZN": "Cloud & Internet Platforms",
    "ANET": "Networking Infrastructure",
    "ARM": "Semiconductors - Chip Design",
    "ASML": "Semiconductors - Lithography",
    "ASTS": "Space & Satellite Communications",
    "ATD": "Consumer Staples / Retail",
    "AXON": "Public Safety Technology",
    "BNS": "Financials",
    "BTCUSD": "Crypto",
    "BTDR": "Crypto Infrastructure",
    "CCO": "Uranium & Nuclear Fuel",
    "CLSK": "Crypto Infrastructure",
    "COST": "Consumer Staples / Retail",
    "CP": "Industrials / Rail",
    "CU": "Utilities",
    "CUPR": "Materials",
    "DUOL": "Software",
    "ENB": "Energy Infrastructure",
    "ETHUSD": "Crypto",
    "FLNC": "Energy Storage",
    "FNV": "Precious Metals",
    "FTS": "Utilities",
    "GME": "Consumer Discretionary",
    "GOOG": "Cloud & Internet Platforms",
    "HIMS": "Digital Health",
    "IBIT": "Crypto ETF",
    "IREN": "AI Data Centers & Crypto Infrastructure",
    "ISRG": "Medical Technology",
    "KITS": "Consumer Health",
    "L": "Financials",
    "LITE": "Optical & Networking",
    "LMT": "Aerospace & Defense",
    "LULU": "Consumer Discretionary",
    "MCD": "Consumer Staples / Restaurants",
    "MCHI": "ETF / China Equity",
    "MELI": "E-commerce & Fintech",
    "META": "Cloud & Internet Platforms",
    "MFC": "Financials",
    "MSFT": "Software",
    "MU": "Semiconductors - Memory",
    "NBIS": "AI Cloud Infrastructure",
    "NFLX": "Media & Streaming",
    "NVO": "Healthcare",
    "NVDA": "Semiconductors - Chip Design",
    "OUST": "Sensors & Robotics",
    "PANW": "Cybersecurity",
    "PAVE": "ETF / Infrastructure",
    "POET": "Optical & Networking",
    "PZA": "Consumer Staples / Restaurants",
    "QQC.F": "ETF / Nasdaq",
    "RBRK": "Cybersecurity",
    "RKLB": "Space & Satellite Communications",
    "RY": "Financials",
    "SHLS": "Solar Infrastructure",
    "SLV": "Precious Metals ETF",
    "SNOW": "Software",
    "SOBO": "Energy Infrastructure",
    "SOFI": "Fintech",
    "SPY": "ETF / US Equity",
    "SYM": "Automation & Robotics",
    "T": "Telecom",
    "TD": "Financials",
    "TOI": "Software",
    "TRP": "Energy Infrastructure",
    "TSM": "Semiconductors - Leading-Edge Foundry",
    "USDCUSD": "Crypto",
    "V": "Payments",
    "VCN": "ETF / Canada Equity",
    "VDY": "ETF / Canada Dividend",
    "VFV": "ETF / US Equity",
    "VGRO": "ETF / Balanced",
    "VOO": "ETF / US Equity",
    "VRT": "AI Data Centers & Power",
    "VST": "Power & Utilities",
    "XEC": "ETF / Emerging Markets",
    "XEF": "ETF / Developed Markets",
    "XIU": "ETF / Canada Equity",
    "ZEQT": "ETF / Global Equity",
    "ZETA": "Software",
    "ZGLD": "Precious Metals ETF",
    "ZMMK": "Money Market",
    "ZQQ": "ETF / Nasdaq",
    "ZSP": "ETF / US Equity",
}
VARIABLE_STRATEGY_START = date(2026, 1, 31)
VARIABLE_ENTRY_USD = Decimal("1000")
MASTER_POSITION_LIMIT = 25
MASTER_SECTOR_LIMIT = 5
WEALTHSIMPLE_FX_FEE = Decimal(str(WEALTHSIMPLE_FX_FEE_RATE))
SUMMARY_KEYS = (
    "investor",
    "initial_value",
    "current_value",
    "gain_loss",
    "return_pct",
    "daily_change_pct",
    "five_day_change_pct",
    "monthly_change_pct",
    "position_count",
    "source",
)
MAIN_PRIORITY_PORTFOLIOS = {
    VARIABLE_STRATEGY_NAME,
    MASTER_STRATEGY_NAME,
    "watchlist-variable-news-optimized-experimental",
    HYBRID_NEWS_OPTIMIZED_STRATEGY_NAME,
    ANALYSIS_DRIVEN_STRATEGY_NAME,
}
LOW_PRIORITY_PORTFOLIOS = {
    MASS_CHANGE_STRATEGY_NAME,
    VARIABLE_BUY_ONLY_NAME,
    VARIABLE_MORE_SIGNALS_NAME,
}


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


def fixed_change_fields(
    daily: Decimal,
    five_day: Decimal,
    monthly: Decimal,
) -> dict[str, float]:
    return {
        "daily_change_pct": as_float(daily),
        "five_day_change_pct": as_float(five_day),
        "monthly_change_pct": as_float(monthly),
    }


def fixed_changes_from_bars(
    bars: tuple[Bar, ...],
    end: date | None,
) -> dict[str, float]:
    latest = on_or_before(bars, end)
    if not latest:
        return fixed_change_fields(Decimal("0"), Decimal("0"), Decimal("0"))
    history = [bar for bar in bars if bar.day <= latest.day]
    latest_index = len(history) - 1
    daily = (
        pct_change(latest.close, history[latest_index - 1].close)
        if latest_index >= 1
        else Decimal("0")
    )
    five_day = (
        pct_change(latest.close, history[latest_index - 5].close)
        if latest_index >= 5
        else Decimal("0")
    )
    monthly_bar = on_or_before(tuple(history), latest.day - timedelta(days=30))
    monthly = pct_change(latest.close, monthly_bar.close) if monthly_bar else Decimal("0")
    return fixed_change_fields(daily, five_day, monthly)


def fixed_changes_from_series(
    rows: list[dict[str, object]],
    key: str = "value",
) -> dict[str, float]:
    if not rows:
        return fixed_change_fields(Decimal("0"), Decimal("0"), Decimal("0"))
    latest_day = date.fromisoformat(str(rows[-1]["date"]))
    latest_value = Decimal(str(rows[-1][key]))
    daily_value = Decimal(str(rows[-2][key])) if len(rows) >= 2 else latest_value
    five_day_value = Decimal(str(rows[-6][key])) if len(rows) >= 6 else latest_value
    monthly_row = next(
        (
            row
            for row in reversed(rows)
            if date.fromisoformat(str(row["date"])) <= latest_day - timedelta(days=30)
        ),
        None,
    )
    monthly_value = Decimal(str(monthly_row[key])) if monthly_row else latest_value
    return fixed_change_fields(
        pct_change(latest_value, daily_value),
        pct_change(latest_value, five_day_value),
        pct_change(latest_value, monthly_value),
    )


def weighted_fixed_changes(parts: list[dict[str, Decimal]]) -> dict[str, float]:
    current = sum((part["current"] for part in parts), Decimal("0"))
    daily = sum((part["daily"] for part in parts), Decimal("0"))
    five_day = sum((part["five_day"] for part in parts), Decimal("0"))
    monthly = sum((part["monthly"] for part in parts), Decimal("0"))
    return fixed_change_fields(
        pct_change(current, daily),
        pct_change(current, five_day),
        pct_change(current, monthly),
    )


def benchmark_comparison(
    series: list[dict[str, object]],
    benchmark_symbol: str = "SPY",
) -> dict[str, object]:
    if len(series) < 2:
        return {
            "benchmark": benchmark_symbol,
            "benchmark_return_pct": 0,
            "alpha_pct": 0,
            "volatility_pct": 0,
            "max_drawdown_pct": 0,
            "best_day_pct": 0,
            "worst_day_pct": 0,
            "win_rate_vs_benchmark_pct": 0,
            "benchmark_series": [],
        }
    try:
        _, benchmark_bars = fetch_chart(benchmark_symbol)
    except Exception as exc:
        return {
            "benchmark": benchmark_symbol,
            "benchmark_return_pct": 0,
            "alpha_pct": 0,
            "volatility_pct": 0,
            "max_drawdown_pct": 0,
            "best_day_pct": 0,
            "worst_day_pct": 0,
            "win_rate_vs_benchmark_pct": 0,
            "benchmark_series": [],
            "warning": str(exc),
        }

    first_value = Decimal(str(series[0]["value"]))
    last_value = Decimal(str(series[-1]["value"]))
    first_day = date.fromisoformat(str(series[0]["date"]))
    last_day = date.fromisoformat(str(series[-1]["date"]))
    first_benchmark = on_or_before(benchmark_bars, first_day)
    last_benchmark = on_or_before(benchmark_bars, last_day)
    if not first_value or not first_benchmark or not last_benchmark:
        return {
            "benchmark": benchmark_symbol,
            "benchmark_return_pct": 0,
            "alpha_pct": 0,
            "volatility_pct": 0,
            "max_drawdown_pct": 0,
            "best_day_pct": 0,
            "worst_day_pct": 0,
            "win_rate_vs_benchmark_pct": 0,
            "benchmark_series": [],
            "warning": "missing benchmark baseline",
        }

    benchmark_series: list[dict[str, object]] = []
    portfolio_daily_returns: list[Decimal] = []
    benchmark_daily_returns: list[Decimal] = []
    peak = first_value
    max_drawdown = Decimal("0")
    previous_value = first_value
    previous_benchmark = first_benchmark.close
    wins = 0
    comparisons = 0

    for index, row in enumerate(series):
        row_day = date.fromisoformat(str(row["date"]))
        row_value = Decimal(str(row["value"]))
        benchmark_bar = on_or_before(benchmark_bars, row_day)
        if benchmark_bar:
            normalized_value = first_value * benchmark_bar.close / first_benchmark.close
            benchmark_series.append(
                {
                    "date": row_day.isoformat(),
                    "value": as_float(normalized_value),
                    "return_pct": as_float(pct_change(benchmark_bar.close, first_benchmark.close)),
                }
            )
        if row_value > peak:
            peak = row_value
        drawdown = pct_change(row_value, peak)
        if drawdown < max_drawdown:
            max_drawdown = drawdown
        if index == 0 or not benchmark_bar:
            previous_value = row_value
            if benchmark_bar:
                previous_benchmark = benchmark_bar.close
            continue
        portfolio_return = pct_change(row_value, previous_value)
        benchmark_return = pct_change(benchmark_bar.close, previous_benchmark)
        portfolio_daily_returns.append(portfolio_return)
        benchmark_daily_returns.append(benchmark_return)
        if portfolio_return > benchmark_return:
            wins += 1
        comparisons += 1
        previous_value = row_value
        previous_benchmark = benchmark_bar.close

    portfolio_return = pct_change(last_value, first_value)
    benchmark_return = pct_change(last_benchmark.close, first_benchmark.close)
    volatility = Decimal("0")
    if len(portfolio_daily_returns) >= 2:
        daily_values = [float(value) for value in portfolio_daily_returns]
        mean = sum(daily_values) / len(daily_values)
        variance = sum((value - mean) ** 2 for value in daily_values) / (len(daily_values) - 1)
        volatility = Decimal(str(math.sqrt(variance) * math.sqrt(252)))
    return {
        "benchmark": benchmark_symbol,
        "benchmark_return_pct": as_float(benchmark_return),
        "alpha_pct": as_float(portfolio_return - benchmark_return),
        "volatility_pct": as_float(volatility),
        "max_drawdown_pct": as_float(max_drawdown),
        "best_day_pct": as_float(max(portfolio_daily_returns, default=Decimal("0"))),
        "worst_day_pct": as_float(min(portfolio_daily_returns, default=Decimal("0"))),
        "win_rate_vs_benchmark_pct": as_float(
            Decimal(wins) / Decimal(comparisons) * 100 if comparisons else Decimal("0")
        ),
        "benchmark_series": benchmark_series,
    }


def prior_value_from_return(current: Decimal, return_pct: object) -> Decimal:
    rate = Decimal(str(return_pct)) / Decimal("100")
    return current / (Decimal("1") + rate) if rate != Decimal("-1") else current


def with_variable_fx_fees(detail: dict[str, object]) -> dict[str, object]:
    executed = detail.get("simulated_trades", [])
    if not isinstance(executed, list):
        return detail
    fees = sum(
        (
            Decimal(str(row["usd_amount"])) * WEALTHSIMPLE_FX_FEE
            for row in executed
            if isinstance(row, dict) and row.get("usd_amount") is not None
        ),
        Decimal("0"),
    )
    initial = Decimal(str(detail["initial_value"]))
    adjusted_gain = Decimal(str(detail["gain_loss"])) - fees
    adjusted_current = initial + adjusted_gain
    fee_rows = [
        (
            date.fromisoformat(str(row["date"])),
            Decimal(str(row["usd_amount"])) * WEALTHSIMPLE_FX_FEE,
        )
        for row in executed
        if isinstance(row, dict) and row.get("usd_amount") is not None
    ]
    series = []
    for row in detail["series"]:
        day = date.fromisoformat(str(row["date"]))
        cumulative_fees = sum(
            (fee for fee_day, fee in fee_rows if fee_day <= day),
            Decimal("0"),
        )
        series.append(
            {
                **row,
                "value": as_float(Decimal(str(row["value"])) - cumulative_fees),
                "gain_loss": as_float(Decimal(str(row["gain_loss"])) - cumulative_fees),
            }
        )
    positions = [
        {
            **position,
            "current_value": as_float(Decimal(str(position["current_value"])) - VARIABLE_ENTRY_USD * WEALTHSIMPLE_FX_FEE),
            "gain_loss": as_float(Decimal(str(position["gain_loss"])) - VARIABLE_ENTRY_USD * WEALTHSIMPLE_FX_FEE),
            "return_pct": as_float(
                pct_change(
                    Decimal(str(position["current_value"])) - VARIABLE_ENTRY_USD * WEALTHSIMPLE_FX_FEE,
                    VARIABLE_ENTRY_USD,
                )
            ),
        }
        for position in detail["positions"]
    ]
    realized_positions = [
        {
            **position,
            "ending_value": as_float(
                Decimal(str(position["ending_value"]))
                - (
                    VARIABLE_ENTRY_USD
                    + Decimal(str(position["ending_value"]))
                )
                * WEALTHSIMPLE_FX_FEE
            ),
            "gain_loss": as_float(
                Decimal(str(position["gain_loss"]))
                - (
                    VARIABLE_ENTRY_USD
                    + Decimal(str(position["ending_value"]))
                )
                * WEALTHSIMPLE_FX_FEE
            ),
            "return_pct": as_float(
                pct_change(
                    Decimal(str(position["ending_value"]))
                    - (
                        VARIABLE_ENTRY_USD
                        + Decimal(str(position["ending_value"]))
                    )
                    * WEALTHSIMPLE_FX_FEE,
                    VARIABLE_ENTRY_USD,
                )
            ),
        }
        for position in detail.get("realized_positions", [])
    ]
    category_stats = []
    for row in detail["category_stats"]:
        category_fees = sum(
            (
                Decimal(str(trade["usd_amount"])) * WEALTHSIMPLE_FX_FEE
                for trade in executed
                if isinstance(trade, dict)
                and trade.get("entry_signal") == row["category"]
                and trade.get("usd_amount") is not None
            ),
            Decimal("0"),
        )
        ending_value = Decimal(str(row["ending_value"])) - category_fees
        deployed = Decimal(str(row["deployed_capital"]))
        category_stats.append(
            {
                **row,
                "ending_value": as_float(ending_value),
                "gain_loss": as_float(ending_value - deployed),
                "return_pct": as_float(pct_change(ending_value, deployed)),
            }
        )
    return {
        **detail,
        "current_value": as_float(adjusted_current),
        "gain_loss": as_float(adjusted_gain),
        "return_pct": as_float(pct_change(adjusted_current, initial)),
        **fixed_changes_from_series(series),
        "positions": positions,
        "realized_positions": realized_positions,
        "series": series,
        "category_stats": category_stats,
        "wealthsimple_fx_fees_enabled": True,
        "wealthsimple_fx_fees_estimate": as_float(fees),
    }


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


def read_mass_change_watchlist() -> list[dict[str, str]]:
    if not MASS_CHANGE_WATCHLIST_FILE.exists():
        return []
    with MASS_CHANGE_WATCHLIST_FILE.open(newline="", encoding="utf-8-sig") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if row.get("ticker") and row.get("security_type")
        ]


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
    for ticker, security_type in mass_change_assets():
        owners[(ticker, security_type)].add(MASS_CHANGE_STRATEGY_NAME)
    return {asset: sorted(names) for asset, names in owners.items()}


def mass_change_assets() -> list[tuple[str, str]]:
    return sorted(
        {
            (row["ticker"].strip().upper(), row["security_type"].strip().lower())
            for row in read_mass_change_watchlist()
            if row.get("ticker") and row.get("security_type")
        }
    )


def mass_change_sector_by_asset() -> dict[tuple[str, str], str]:
    return {
        (row["ticker"].strip().upper(), row["security_type"].strip().lower()): row["sector"].strip()
        for row in read_mass_change_watchlist()
        if row.get("ticker") and row.get("security_type") and row.get("sector")
    }


def sector_for_asset(
    ticker: str,
    security_type: str,
    owners: list[str],
) -> tuple[str, str]:
    for owner in owners:
        label = SECTOR_OWNER_LABELS.get(owner)
        if label:
            return label, f"owner:{owner}"
    mass_sector = mass_change_sector_by_asset().get((ticker, security_type))
    if mass_sector:
        return mass_sector, "mass-change-watchlist"
    override = TICKER_SECTOR_OVERRIDES.get(ticker)
    if override:
        return override, "ticker-map"
    if security_type == "crypto":
        return "Crypto", "security-type"
    if security_type == "etf":
        return "ETF / Other", "security-type"
    return "Unclassified", "fallback"


def tracked_stock_assets() -> list[tuple[str, str]]:
    return sorted(
        {
            (trade["ticker"], trade["security_type"])
            for trade in read_trades()
            if trade["security_type"] == "stock"
        }
        | {
            (ticker, security_type)
            for ticker, security_type in mass_change_assets()
            if security_type == "stock"
        }
    )


def hybrid_news_optimized_assets() -> list[tuple[str, str]]:
    return sorted(set(tracked_stock_assets()) | set(mass_change_assets()))


STRATEGY_LAB_ENTRY_RULES = {
    "any": None,
    "fresh": {"fresh"},
    "strict": {"strict"},
    "near": {"near"},
    "fresh-or-strict": {"fresh", "strict"},
}
STRATEGY_LAB_ENTRY_NEWS_RULES = {"ignore", "active", "accelerating"}
STRATEGY_LAB_EXIT_RULES = {
    "signal-disappears": {"more_signals_exit": False, "news_rule": None},
    "technical-deterioration": {"more_signals_exit": True, "news_rule": None},
    "hold-while-news-active": {"more_signals_exit": False, "news_rule": "hold-while-news-active"},
    "confirm-news-cooling": {"more_signals_exit": False, "news_rule": "confirm-news-cooling"},
    "early-exit-on-news-cooling": {"more_signals_exit": False, "news_rule": "early-exit-on-news-cooling"},
    "optimized-grid-winner": {"more_signals_exit": False, "news_rule": "optimized-grid-winner"},
}
STRATEGY_LAB_UNIVERSES = {"tracked-stocks", "mass-change", "hybrid"}


def strategy_lab_detail(
    start: date,
    end: date | None,
    entry_signal_rule: str = "any",
    entry_news_rule: str = "ignore",
    exit_rule: str = "signal-disappears",
    universe: str = "tracked-stocks",
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    entry_signal_rule = entry_signal_rule.casefold()
    entry_news_rule = entry_news_rule.casefold()
    exit_rule = exit_rule.casefold()
    universe = universe.casefold()
    if entry_signal_rule not in STRATEGY_LAB_ENTRY_RULES:
        raise ValueError(f"unknown entry_signal_rule: {entry_signal_rule}")
    if entry_news_rule not in STRATEGY_LAB_ENTRY_NEWS_RULES:
        raise ValueError(f"unknown entry_news_rule: {entry_news_rule}")
    if exit_rule not in STRATEGY_LAB_EXIT_RULES:
        raise ValueError(f"unknown exit_rule: {exit_rule}")
    if universe not in STRATEGY_LAB_UNIVERSES:
        raise ValueError(f"unknown universe: {universe}")

    universe_assets = None
    if universe == "mass-change":
        universe_assets = mass_change_assets()
    elif universe == "hybrid":
        universe_assets = hybrid_news_optimized_assets()

    exit_config = STRATEGY_LAB_EXIT_RULES[exit_rule]
    detail = variable_strategy_detail(
        start,
        end,
        strategy_name="strategy-lab-preview",
        more_signals_exit=bool(exit_config["more_signals_exit"]),
        news_rule=exit_config["news_rule"],
        entry_categories=STRATEGY_LAB_ENTRY_RULES[entry_signal_rule],
        entry_news_rule=entry_news_rule,
        apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        universe_assets=universe_assets,
        news_note=(
            "Strategy Lab preview. This is an unsaved backtest using the selected "
            "entry, news, exit, and universe settings."
        ),
    )
    return {
        **detail,
        "lab_config": {
            "entry_signal_rule": entry_signal_rule,
            "entry_news_rule": entry_news_rule,
            "exit_rule": exit_rule,
            "universe": universe,
            "position_size": as_float(VARIABLE_ENTRY_USD),
            "saved": False,
        },
    }


def registry_strategy_config(row: dict[str, object]) -> dict[str, str]:
    entry_rule = str(row.get("entry_rule") or "").casefold()
    exit_rule = str(row.get("exit_rule") or "").casefold()
    news_rule = str(row.get("news_rule") or "").casefold()
    universe_rule = str(row.get("universe") or "").casefold()

    if "fresh or strict" in entry_rule:
        entry_signal_rule = "fresh-or-strict"
    elif "fresh" in entry_rule:
        entry_signal_rule = "fresh"
    elif "strict" in entry_rule:
        entry_signal_rule = "strict"
    elif "near" in entry_rule:
        entry_signal_rule = "near"
    elif "non-none" in entry_rule or "mass-change universe technical signal" in entry_rule:
        entry_signal_rule = "any"
    else:
        raise ValueError("strategy entry rule is not runnable by Strategy Lab yet")

    if "accelerating" in news_rule or "accelerating" in entry_rule:
        entry_news_rule = "accelerating"
    elif "active" in news_rule or "active news" in entry_rule:
        entry_news_rule = "active"
    else:
        entry_news_rule = "ignore"

    if "twenty" in exit_rule or "zero-article" in exit_rule or "optimized" in exit_rule:
        exit_rule_name = "optimized-grid-winner"
    elif "cooling" in exit_rule and "earlier" in exit_rule:
        exit_rule_name = "early-exit-on-news-cooling"
    elif "cooling" in exit_rule:
        exit_rule_name = "confirm-news-cooling"
    elif "news remains active" in exit_rule or "hold while news" in exit_rule:
        exit_rule_name = "hold-while-news-active"
    elif "ten" in exit_rule or "technical deterioration" in exit_rule or "longer technical" in exit_rule:
        exit_rule_name = "technical-deterioration"
    elif "signal becomes none" in exit_rule or "signal disappears" in exit_rule or "never sell" in exit_rule:
        exit_rule_name = "signal-disappears"
    else:
        raise ValueError("strategy exit rule is not runnable by Strategy Lab yet")

    if "mass-change" in universe_rule and "tracked" in universe_rule:
        universe = "hybrid"
    elif "mass-change" in universe_rule:
        universe = "mass-change"
    elif "tracked" in universe_rule:
        universe = "tracked-stocks"
    else:
        universe = "tracked-stocks"

    return {
        "entry_signal_rule": entry_signal_rule,
        "entry_news_rule": entry_news_rule,
        "exit_rule": exit_rule_name,
        "universe": universe,
    }


def saved_strategy_preview_detail(
    strategy: dict[str, object],
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    config = registry_strategy_config(strategy)
    detail = strategy_lab_detail(
        start,
        end,
        apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        **config,
    )
    return {
        **detail,
        "investor": str(strategy["strategy_name"]),
        "source": "saved-strategy-registry-preview",
        "registry_strategy": strategy,
        "note": (
            "Saved strategy registry preview. The row is interpreted through "
            "the current Strategy Lab rule mapper and appears in the main "
            "portfolio ranking when the rule set is supported."
        ),
    }


def saved_strategy_dashboard_summaries(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> list[dict[str, object]]:
    from backend.strategy_registry_service import read_strategies

    summaries: list[dict[str, object]] = []
    for strategy in read_strategies(include_retired=False):
        try:
            detail = saved_strategy_preview_detail(
                strategy,
                start,
                end,
                apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
            )
        except ValueError:
            continue
        detail = {**detail, "source": "saved-strategy-registry-preview"}
        summaries.append(
            {
                key: detail[key]
                for key in SUMMARY_KEYS
            }
            | {"warnings": []}
        )
    return summaries


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
    benchmark_bars: tuple[Bar, ...] | None = None,
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
    benchmark_return = Decimal("0")
    relative_strength = return_pct
    if benchmark_bars:
        benchmark_baseline = on_or_before(benchmark_bars, baseline.day)
        benchmark_current = on_or_before(benchmark_bars, current.day)
        if benchmark_baseline and benchmark_current:
            benchmark_return = pct_change(benchmark_current.close, benchmark_baseline.close)
            relative_strength = return_pct - benchmark_return
    recent_high_bars = bars[max(0, len(bars) - max(21, len(horizon_bars) + 1)) : -1]
    distance = pct_change(current.close, max(bar.close for bar in recent_high_bars))
    momentum_score = clamp(return_pct / momentum_threshold * 100)
    volume_score = clamp((volume_ratio - 1) / Decimal("0.5") * 100)
    high_score = clamp((distance + 10) / 10 * 100)
    relative_strength_score = clamp((relative_strength + Decimal("5")) / Decimal("15") * 100)
    score = (
        momentum_score * Decimal("0.35")
        + volume_score * Decimal("0.30")
        + high_score * Decimal("0.15")
        + relative_strength_score * Decimal("0.20")
    )
    strict = return_pct >= momentum_threshold and volume_ratio >= Decimal("1.5") and distance >= -2
    near = volume_ratio >= Decimal("1.25") and distance >= -2
    return {
        "key": key,
        "label": label,
        "start_date": baseline.day.isoformat(),
        "as_of": current.day.isoformat(),
        "return_pct": as_float(return_pct),
        "benchmark_return_pct": as_float(benchmark_return),
        "relative_strength_pct": as_float(relative_strength),
        "volume_ratio": as_float(volume_ratio),
        "distance_to_20d_high_pct": as_float(distance),
        "score": as_float(score),
        "score_components": {
            "momentum": as_float(momentum_score),
            "volume": as_float(volume_score),
            "trend_quality": as_float(high_score),
            "relative_strength": as_float(relative_strength_score),
        },
        "classification": "strict" if strict else ("near" if near else "none"),
        "fresh_priority": bool(strict and return_pct <= momentum_threshold * Decimal("2.5")),
    }


def live_signal(bars: tuple[Bar, ...]) -> dict[str, object] | None:
    try:
        _, benchmark_bars = fetch_chart("SPY")
    except Exception:
        benchmark_bars = None
    horizons = {
        key: signal
        for key, label, sessions, calendar_days, threshold in SIGNAL_HORIZONS
        if (
            signal := horizon_signal(
                bars, key, label, sessions, calendar_days, threshold, benchmark_bars
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
        "five_day_relative_strength_pct": five_day["relative_strength_pct"],
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


def portfolio_priority(row: dict[str, object]) -> tuple[str, str | None]:
    investor = str(row.get("investor") or "").casefold()
    source = str(row.get("source") or "").casefold()
    position_count = int(row.get("position_count") or 0)
    if investor in MAIN_PRIORITY_PORTFOLIOS:
        return "main", None
    if source in {"paper-ledger", "wealthsimple-import"}:
        return "main", None
    if source.startswith("saved-strategy-registry"):
        return "low", "Saved Strategy Lab experiments stay available but are hidden from the main dashboard by default."
    if investor in LOW_PRIORITY_PORTFOLIOS:
        return "low", "Research or discovery strategy; useful for comparison but not a primary decision portfolio."
    if investor.startswith("analyst-"):
        return "low", "Public analyst-pick basket; useful as reference data, not an actively managed strategy."
    if investor.startswith("watchlist-variable-buy-only-"):
        return "low", "Category-specific buy-only diagnostic variant."
    if investor.startswith("watchlist-variable-more-signals-"):
        return "low", "Category-specific technical-exit diagnostic variant."
    if investor in VARIABLE_TECHNICAL_STRATEGIES:
        return "low", "Category-specific technical signal diagnostic variant."
    if investor in NEWS_STRATEGIES and investor not in MAIN_PRIORITY_PORTFOLIOS:
        return "low", "News-strategy variant kept for research comparison; main page focuses on optimized/news-analysis strategies."
    if source.startswith("derived") and position_count == 0:
        return "low", "No active positions in the selected window."
    return "main", None


def add_portfolio_priority(row: dict[str, object]) -> dict[str, object]:
    priority, reason = portfolio_priority(row)
    return {
        **row,
        "portfolio_priority": priority,
        "portfolio_priority_reason": reason,
    }


def _decimal_from_nested(mapping: dict[str, object], *keys: str, default: str = "0") -> Decimal:
    value: object = mapping
    for key in keys:
        if not isinstance(value, dict):
            return Decimal(default)
        value = value.get(key, default)
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def analysis_entry_score(
    signal: dict[str, object] | None,
    category: str,
    news: dict[str, Decimal | int | None],
) -> Decimal:
    if not signal:
        return Decimal("0")
    horizons = signal.get("horizons", {}) if isinstance(signal.get("horizons"), dict) else {}
    five_day = horizons.get("5d", {}) if isinstance(horizons.get("5d"), dict) else {}
    one_week = horizons.get("1w", {}) if isinstance(horizons.get("1w"), dict) else {}
    one_month = horizons.get("1m", {}) if isinstance(horizons.get("1m"), dict) else {}
    three_month = horizons.get("3m", {}) if isinstance(horizons.get("3m"), dict) else {}
    score = Decimal(str(signal.get("overall_score", 0)))
    score += {"fresh": Decimal("14"), "strict": Decimal("9"), "near": Decimal("-8")}.get(category, Decimal("0"))

    articles_7d = int(news["articles_7d"])
    articles_prior_7d = int(news["articles_prior_7d"])
    if articles_7d > 0:
        score += Decimal("8")
    if articles_7d > articles_prior_7d:
        score += Decimal("14")
    weekly_velocity = news.get("weekly_velocity")
    if isinstance(weekly_velocity, Decimal) and weekly_velocity > Decimal("1"):
        score += min((weekly_velocity - Decimal("1")) * Decimal("4"), Decimal("10"))

    five_day_rel = _decimal_from_nested(five_day, "relative_strength_pct")
    one_month_rel = _decimal_from_nested(one_month, "relative_strength_pct")
    five_day_volume = _decimal_from_nested(five_day, "volume_ratio")
    distance_to_high = _decimal_from_nested(five_day, "distance_to_20d_high_pct")
    five_day_return = _decimal_from_nested(five_day, "return_pct")
    one_month_return = _decimal_from_nested(one_month, "return_pct")
    three_month_return = _decimal_from_nested(three_month, "return_pct")

    if five_day_rel > 0:
        score += min(five_day_rel * Decimal("0.7"), Decimal("12"))
    else:
        score += max(five_day_rel * Decimal("0.8"), Decimal("-12"))
    if one_month_rel > 0:
        score += min(one_month_rel * Decimal("0.35"), Decimal("10"))
    elif one_month_rel < Decimal("-3"):
        score -= Decimal("8")
    if five_day_volume >= Decimal("1.25"):
        score += min((five_day_volume - Decimal("1")) * Decimal("8"), Decimal("12"))
    elif five_day_volume < Decimal("0.85"):
        score -= Decimal("5")
    if distance_to_high >= Decimal("-3"):
        score += Decimal("6")
    elif distance_to_high < Decimal("-10"):
        score -= Decimal("10")

    confirming_horizons = 0
    for horizon in (five_day, one_week, one_month):
        horizon_rel = _decimal_from_nested(horizon, "relative_strength_pct")
        horizon_score = _decimal_from_nested(horizon, "score")
        if horizon_rel > 0 and horizon_score >= Decimal("45"):
            confirming_horizons += 1
    score += Decimal(confirming_horizons * 3)

    if five_day_return > Decimal("55"):
        score -= Decimal("8")
    if one_month_return > Decimal("120"):
        score -= Decimal("14")
    if three_month_return > Decimal("220"):
        score -= Decimal("10")
    if one_month_return < Decimal("-10"):
        score -= Decimal("8")
    return score


def variable_strategy_detail(
    start: date,
    end: date | None,
    strategy_name: str = VARIABLE_STRATEGY_NAME,
    more_signals_exit: bool = False,
    news_rule: str | None = None,
    entry_categories: set[str] | None = None,
    entry_news_rule: str = "ignore",
    entry_analysis_rule: str = "ignore",
    apply_wealthsimple_fx_fees: bool = False,
    universe_assets: list[tuple[str, str]] | None = None,
    news_note: str | None = None,
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
    asset_types: dict[str, str] = {}
    for ticker, security_type in (universe_assets if universe_assets is not None else tracked_stock_assets()):
        symbol = yahoo_symbol(ticker, security_type)
        try:
            _, bars = fetch_chart(symbol)
        except Exception:
            continue
        if bars:
            charts[ticker] = bars
            asset_types[ticker] = security_type

    active: dict[str, dict[str, object]] = {}
    cycles: list[dict[str, object]] = []
    series: list[dict[str, object]] = []
    sector_exposure: list[dict[str, object]] = []
    signal_mix: list[dict[str, object]] = []
    deployed = Decimal("0")
    realized = Decimal("0")
    previous_session = on_or_before(market_bars, VARIABLE_STRATEGY_START - timedelta(days=1))
    daily_news = load_daily_news_counts()
    news_counts = daily_news.get("tickers", {})
    if not isinstance(news_counts, dict):
        news_counts = {}

    def observed_state(
        observed_day: date,
    ) -> tuple[
        dict[str, str],
        dict[str, dict[str, object] | None],
        dict[str, dict[str, Decimal | int | None]],
    ]:
        desired: dict[str, str] = {}
        observed: dict[str, dict[str, object] | None] = {}
        observed_news: dict[str, dict[str, Decimal | int | None]] = {}
        for ticker, bars in charts.items():
            signal_bars = tuple(bar for bar in bars if bar.day <= observed_day)
            observed[ticker] = live_signal(signal_bars)
            ticker_counts = news_counts.get(ticker, {})
            observed_news[ticker] = news_metrics(
                ticker_counts if isinstance(ticker_counts, dict) else {},
                observed_day,
            )
            category = entry_signal(observed[ticker])
            if category and (entry_categories is None or category in entry_categories):
                desired[ticker] = category
        return desired, observed, observed_news

    def entry_news_matches(news: dict[str, Decimal | int | None]) -> bool:
        if entry_news_rule == "active":
            return int(news["articles_7d"]) > 0
        if entry_news_rule == "accelerating":
            return int(news["articles_7d"]) > int(news["articles_prior_7d"])
        return True

    def entry_analysis_matches(
        signal: dict[str, object] | None,
        category: str,
        news: dict[str, Decimal | int | None],
    ) -> bool:
        if entry_analysis_rule == "quality-score":
            return analysis_entry_score(signal, category, news) >= ANALYSIS_ENTRY_SCORE
        return True

    def exit_matches(
        position: dict[str, object],
        signal: dict[str, object] | None,
        news: dict[str, Decimal | int | None],
    ) -> bool:
        one_month = (signal or {}).get("horizons", {}).get("1m", {})
        one_month_return = Decimal(str(one_month.get("return_pct", "0")))
        if news_rule:
            return news_should_exit(
                news_rule,
                int(position["none_streak"]),
                one_month_return,
                news,
            )
        return (
            int(position["none_streak"]) >= 10
            and one_month_return <= Decimal("-5")
            if more_signals_exit
            else int(position["none_streak"]) >= 1
        )

    for session in sessions:
        if not previous_session:
            previous_session = on_or_before(market_bars, session - timedelta(days=1))
        desired, observed, observed_news = observed_state(previous_session.day)

        for ticker in set(active) & set(desired):
            active[ticker]["none_streak"] = 0

        for ticker in sorted(set(active) - set(desired)):
            price_bar = on_or_before(charts[ticker], session)
            if not price_bar or price_bar.day <= previous_session.day:
                continue
            position = active.pop(ticker)
            position["none_streak"] = int(position.get("none_streak", 0)) + 1
            if not exit_matches(position, observed[ticker], observed_news[ticker]):
                active[ticker] = position
                continue
            proceeds = Decimal(str(position["shares"])) * price_bar.close
            pnl = proceeds - VARIABLE_ENTRY_USD
            realized += pnl
            cycles.append(
                {
                    **position,
                    "exit_signal_observed_date": previous_session.day.isoformat(),
                    "exit_date": price_bar.day.isoformat(),
                    "exit_price": as_float(price_bar.close),
                    "ending_value": as_float(proceeds),
                    "gain_loss": as_float(pnl),
                    "return_pct": as_float(pct_change(proceeds, VARIABLE_ENTRY_USD)),
                    "status": "closed",
                }
            )

        for ticker in sorted(set(desired) - set(active)):
            if not entry_news_matches(observed_news[ticker]):
                continue
            if not entry_analysis_matches(observed[ticker], desired[ticker], observed_news[ticker]):
                continue
            price_bar = on_or_before(charts[ticker], session)
            if not price_bar or price_bar.day <= previous_session.day:
                continue
            shares = VARIABLE_ENTRY_USD / price_bar.close
            deployed += VARIABLE_ENTRY_USD
            active[ticker] = {
                "ticker": ticker,
                "entry_signal": desired[ticker],
                "signal_observed_date": previous_session.day.isoformat(),
                "entry_date": price_bar.day.isoformat(),
                "entry_price": as_float(price_bar.close),
                "shares": shares,
                "initial_value": as_float(VARIABLE_ENTRY_USD),
                "none_streak": 0,
            }

        open_value = Decimal("0")
        sector_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for ticker, position in active.items():
            price_bar = on_or_before(charts[ticker], session)
            if price_bar:
                position_value = Decimal(str(position["shares"])) * price_bar.close
                open_value += position_value
                sector, _ = sector_for_asset(
                    ticker,
                    asset_types.get(ticker, "stock"),
                    [strategy_name],
                )
                sector_values[sector] += position_value
        series.append(
            {
                "date": session.isoformat(),
                "value": as_float(deployed + realized + open_value - VARIABLE_ENTRY_USD * len(active)),
                "gain_loss": as_float(realized + open_value - VARIABLE_ENTRY_USD * len(active)),
                "deployed_capital": as_float(deployed),
                "active_positions": len(active),
            }
        )
        sector_exposure.append(
            {
                "date": session.isoformat(),
                "sectors": [
                    {
                        "sector": sector,
                        "value": as_float(value),
                        "weight_pct": as_float(value / open_value * Decimal("100")),
                    }
                    for sector, value in sorted(sector_values.items())
                    if open_value
                ],
            }
        )
        signal_counts: defaultdict[str, int] = defaultdict(int)
        for position in active.values():
            signal_counts[str(position.get("entry_signal") or "unknown")] += 1
        signal_mix.append(
            {
                "date": session.isoformat(),
                "signals": [
                    {
                        "signal": signal,
                        "positions": count,
                        "weight_pct": as_float(Decimal(count) / Decimal(len(active)) * Decimal("100")),
                    }
                    for signal, count in sorted(signal_counts.items())
                    if active
                ],
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
                **fixed_changes_from_bars(charts[ticker], latest_market.day),
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

    simulated_trades: list[dict[str, object]] = []
    for position in [*cycles, *open_positions]:
        simulated_trades.append(
            {
                "date": position["entry_date"],
                "signal_observed_date": position["signal_observed_date"],
                "action": "buy",
                "ticker": position["ticker"],
                "entry_signal": position["entry_signal"],
                "execution_price": position["entry_price"],
                "quantity": as_float(Decimal(str(position["shares"]))),
                "usd_amount": as_float(VARIABLE_ENTRY_USD),
                "gain_loss": None,
            }
        )
    for position in cycles:
        simulated_trades.append(
            {
                "date": position["exit_date"],
                "signal_observed_date": position["exit_signal_observed_date"],
                "action": "sell",
                "ticker": position["ticker"],
                "entry_signal": position["entry_signal"],
                "execution_price": position["exit_price"],
                "quantity": as_float(Decimal(str(position["shares"]))),
                "usd_amount": position["ending_value"],
                "gain_loss": position["gain_loss"],
            }
        )
    simulated_trades.sort(key=lambda row: (row["date"], row["ticker"], row["action"]))

    pending_next_close_orders: list[dict[str, object]] = []
    latest_desired, latest_observed, latest_news = observed_state(latest_market.day)
    for ticker in sorted(set(latest_desired) - set(active)):
        if not entry_news_matches(latest_news[ticker]):
            continue
        if not entry_analysis_matches(latest_observed[ticker], latest_desired[ticker], latest_news[ticker]):
            continue
        pending_next_close_orders.append(
            {
                "date": "next available close",
                "signal_observed_date": latest_market.day.isoformat(),
                "action": "buy",
                "ticker": ticker,
                "entry_signal": latest_desired[ticker],
                "execution_price": None,
                "quantity": None,
                "usd_amount": as_float(VARIABLE_ENTRY_USD),
                "gain_loss": None,
                "status": "pending",
            }
        )
    for ticker in sorted(set(active) - set(latest_desired)):
        position = {**active[ticker]}
        position["none_streak"] = int(position.get("none_streak", 0)) + 1
        if not exit_matches(position, latest_observed[ticker], latest_news[ticker]):
            continue
        pending_next_close_orders.append(
            {
                "date": "next available close",
                "signal_observed_date": latest_market.day.isoformat(),
                "action": "sell",
                "ticker": ticker,
                "entry_signal": position["entry_signal"],
                "execution_price": None,
                "quantity": as_float(Decimal(str(position["shares"]))),
                "usd_amount": None,
                "gain_loss": None,
                "status": "pending",
            }
        )

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
    realized_positions = sorted(cycles, key=lambda row: row["return_pct"], reverse=True)
    visible_series = [
        row
        for row in series
        if date.fromisoformat(str(row["date"])) >= selected_start
    ]
    visible_sector_exposure = [
        row
        for row in sector_exposure
        if date.fromisoformat(str(row["date"])) >= selected_start
    ]
    visible_signal_mix = [
        row
        for row in signal_mix
        if date.fromisoformat(str(row["date"])) >= selected_start
    ]
    detail = {
        "investor": strategy_name,
        "source": (
            "derived-news-analysis-signal-strategy"
            if entry_analysis_rule != "ignore"
            else "derived-news-assisted-signal-strategy"
            if news_rule or entry_news_rule != "ignore"
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
        **fixed_changes_from_series(series),
        "position_count": len(open_positions),
        "positions": open_positions,
        "realized_positions": realized_positions,
        "simulated_trades": simulated_trades,
        "pending_next_close_orders": pending_next_close_orders,
        "execution_convention": "Observe EOD signals and news after one close; execute at the next available EOD close.",
        "series": visible_series,
        "sector_exposure": visible_sector_exposure,
        "signal_mix": visible_signal_mix,
        "benchmark_comparison": benchmark_comparison(visible_series),
        "category_stats": category_rows,
        "category_stats_scope": f"{VARIABLE_STRATEGY_START.isoformat()} to {latest_market.day.isoformat()}",
        "trade_cycles": len(cycles) + len(open_positions),
        "closed_cycles": len(cycles),
        "entry_analysis_rule": entry_analysis_rule,
        "analysis_entry_score_threshold": as_float(ANALYSIS_ENTRY_SCORE)
        if entry_analysis_rule != "ignore"
        else None,
        "news_counts_to_date": daily_news.get("to_date")
        if news_rule or entry_news_rule != "ignore" or entry_analysis_rule != "ignore"
        else None,
        "note": (
            (
                "News + analysis driven EOD strategy. "
                if entry_analysis_rule != "ignore"
                else "News-assisted EOD strategy. "
            )
            + f"{news_note or NEWS_STRATEGIES.get(strategy_name, {}).get('note', 'News-assisted strategy.')} "
            f"Committed Alpaca daily news counts currently end on {daily_news.get('to_date')}. "
            "Signals and news are observed at one close and executed at the next "
            "available close. Each entry deploys $1,000. FX conversion is intentionally ignored."
            if news_rule or entry_news_rule != "ignore" or entry_analysis_rule != "ignore"
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
    return with_variable_fx_fees(detail) if apply_wealthsimple_fx_fees else detail


def variable_strategy_summary(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    detail = variable_strategy_detail(start, end, apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees)
    return {
        key: detail[key]
        for key in SUMMARY_KEYS
    } | {"warnings": []}


def master_candidate_score(
    signal: dict[str, object],
    category: str,
    news: dict[str, Decimal | int | None],
) -> Decimal:
    horizons = signal.get("horizons", {}) if isinstance(signal.get("horizons"), dict) else {}
    five_day = horizons.get("5d", {}) if isinstance(horizons.get("5d"), dict) else {}
    one_month = horizons.get("1m", {}) if isinstance(horizons.get("1m"), dict) else {}
    score = Decimal(str(signal.get("overall_score", 0)))
    score += {"fresh": Decimal("25"), "strict": Decimal("15"), "near": Decimal("5")}.get(category, Decimal("0"))
    if int(news["articles_7d"]) > 0:
        score += Decimal("8")
    if int(news["articles_7d"]) > int(news["articles_prior_7d"]):
        score += Decimal("12")

    relative_strength = Decimal(str(five_day.get("relative_strength_pct", 0)))
    volume_ratio = Decimal(str(five_day.get("volume_ratio", 1)))
    score += clamp(relative_strength, Decimal("0"), Decimal("15")) * Decimal("0.8")
    score += clamp((volume_ratio - Decimal("1")) * Decimal("12"), Decimal("0"), Decimal("12"))

    five_day_return = Decimal(str(five_day.get("return_pct", 0)))
    one_month_return = Decimal(str(one_month.get("return_pct", 0)))
    distance_to_high = Decimal(str(five_day.get("distance_to_20d_high_pct", 0)))
    if five_day_return > Decimal("60"):
        score -= Decimal("10")
    if one_month_return > Decimal("120"):
        score -= Decimal("15")
    if relative_strength < Decimal("-3"):
        score -= Decimal("8")
    if distance_to_high < Decimal("-8"):
        score -= Decimal("8")
    return score


def master_portfolio_detail(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
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

    universe_assets = hybrid_news_optimized_assets()
    owners = owners_by_asset()
    charts: dict[str, tuple[Bar, ...]] = {}
    asset_types: dict[str, str] = {}
    sectors: dict[str, str] = {}
    for ticker, security_type in universe_assets:
        symbol = yahoo_symbol(ticker, security_type)
        try:
            _, bars = fetch_chart(symbol)
        except Exception:
            continue
        if bars:
            charts[ticker] = bars
            asset_types[ticker] = security_type
            sectors[ticker], _ = sector_for_asset(
                ticker,
                security_type,
                owners.get((ticker, security_type), [MASTER_STRATEGY_NAME]),
            )

    daily_news = load_daily_news_counts()
    news_counts = daily_news.get("tickers", {})
    if not isinstance(news_counts, dict):
        news_counts = {}

    def ranked_candidates(observed_day: date) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for ticker, bars in charts.items():
            signal_bars = tuple(bar for bar in bars if bar.day <= observed_day)
            signal = live_signal(signal_bars)
            category = entry_signal(signal)
            if not category or not isinstance(signal, dict):
                continue
            ticker_counts = news_counts.get(ticker, {})
            news = news_metrics(
                ticker_counts if isinstance(ticker_counts, dict) else {},
                observed_day,
            )
            if category == "near" and Decimal(str(signal.get("overall_score", 0))) < Decimal("55") and int(news["articles_7d"]) == 0:
                continue
            master_score = master_candidate_score(signal, category, news)
            if master_score < Decimal("60"):
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "entry_signal": category,
                    "signal": signal,
                    "news": news,
                    "master_score": master_score,
                    "sector": sectors.get(ticker, "Unclassified"),
                }
            )

        return sorted(
            rows,
            key=lambda item: (
                Decimal(str(item["master_score"])),
                Decimal(str(item["signal"].get("overall_score", 0))),
                Decimal(str(item["signal"].get("five_day_relative_strength_pct", 0))),
            ),
            reverse=True,
        )

    def fill_candidates(
        candidates: list[dict[str, object]],
        active_positions: dict[str, dict[str, object]],
    ) -> dict[str, dict[str, object]]:
        selected: dict[str, dict[str, object]] = {}
        sector_counts: defaultdict[str, int] = defaultdict(int)
        for position in active_positions.values():
            sector_counts[str(position.get("sector") or "Unclassified")] += 1
        for row in candidates:
            ticker = str(row["ticker"])
            sector = str(row["sector"])
            if ticker in active_positions:
                continue
            if len(active_positions) + len(selected) >= MASTER_POSITION_LIMIT:
                break
            if sector_counts[sector] >= MASTER_SECTOR_LIMIT:
                continue
            selected[ticker] = row
            sector_counts[sector] += 1
        return selected

    active: dict[str, dict[str, object]] = {}
    cycles: list[dict[str, object]] = []
    series: list[dict[str, object]] = []
    sector_exposure: list[dict[str, object]] = []
    signal_mix: list[dict[str, object]] = []
    deployed = Decimal("0")
    realized = Decimal("0")
    previous_session = on_or_before(market_bars, VARIABLE_STRATEGY_START - timedelta(days=1))

    for session in sessions:
        if not previous_session:
            previous_session = on_or_before(market_bars, session - timedelta(days=1))
        candidates = ranked_candidates(previous_session.day)
        candidate_by_ticker = {str(row["ticker"]): row for row in candidates}
        tickers_to_sell: set[str] = set()
        for ticker, position in list(active.items()):
            row = candidate_by_ticker.get(ticker)
            if row:
                news = row["news"]
                position.update(
                    {
                        "entry_signal": row["entry_signal"],
                        "master_score": as_float(Decimal(str(row["master_score"]))),
                        "news_articles_7d": int(news["articles_7d"]),
                        "news_articles_prior_7d": int(news["articles_prior_7d"]),
                        "below_master_streak": 0,
                    }
                )
            else:
                position["below_master_streak"] = int(position.get("below_master_streak", 0)) + 1
                if int(position["below_master_streak"]) >= 5:
                    tickers_to_sell.add(ticker)

        for ticker in sorted(tickers_to_sell):
            price_bar = on_or_before(charts[ticker], session)
            if not price_bar or price_bar.day <= previous_session.day:
                continue
            position = active.pop(ticker)
            proceeds = Decimal(str(position["shares"])) * price_bar.close
            pnl = proceeds - VARIABLE_ENTRY_USD
            realized += pnl
            cycles.append(
                {
                    **position,
                    "exit_signal_observed_date": previous_session.day.isoformat(),
                    "exit_date": price_bar.day.isoformat(),
                    "exit_price": as_float(price_bar.close),
                    "ending_value": as_float(proceeds),
                    "gain_loss": as_float(pnl),
                    "return_pct": as_float(pct_change(proceeds, VARIABLE_ENTRY_USD)),
                    "status": "closed",
                }
            )

        selected_by_ticker = fill_candidates(candidates, active)
        for ticker, row in sorted(selected_by_ticker.items()):
            if ticker in active:
                continue
            price_bar = on_or_before(charts[ticker], session)
            if not price_bar or price_bar.day <= previous_session.day:
                continue
            shares = VARIABLE_ENTRY_USD / price_bar.close
            deployed += VARIABLE_ENTRY_USD
            news = row["news"]
            active[ticker] = {
                "ticker": ticker,
                "entry_signal": row["entry_signal"],
                "signal_observed_date": previous_session.day.isoformat(),
                "entry_date": price_bar.day.isoformat(),
                "entry_price": as_float(price_bar.close),
                "shares": shares,
                "initial_value": as_float(VARIABLE_ENTRY_USD),
                "master_score": as_float(Decimal(str(row["master_score"]))),
                "news_articles_7d": int(news["articles_7d"]),
                "news_articles_prior_7d": int(news["articles_prior_7d"]),
                "sector": row["sector"],
                "below_master_streak": 0,
            }

        open_value = Decimal("0")
        sector_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for ticker, position in active.items():
            price_bar = on_or_before(charts[ticker], session)
            if price_bar:
                position_value = Decimal(str(position["shares"])) * price_bar.close
                open_value += position_value
                sector_values[str(position.get("sector") or "Unclassified")] += position_value
        series.append(
            {
                "date": session.isoformat(),
                "value": as_float(deployed + realized + open_value - VARIABLE_ENTRY_USD * len(active)),
                "gain_loss": as_float(realized + open_value - VARIABLE_ENTRY_USD * len(active)),
                "deployed_capital": as_float(deployed),
                "active_positions": len(active),
            }
        )
        sector_exposure.append(
            {
                "date": session.isoformat(),
                "sectors": [
                    {
                        "sector": sector,
                        "value": as_float(value),
                        "weight_pct": as_float(value / open_value * Decimal("100")),
                    }
                    for sector, value in sorted(sector_values.items())
                    if open_value
                ],
            }
        )
        signal_counts: defaultdict[str, int] = defaultdict(int)
        for position in active.values():
            signal_counts[str(position.get("entry_signal") or "unknown")] += 1
        signal_mix.append(
            {
                "date": session.isoformat(),
                "signals": [
                    {
                        "signal": signal,
                        "positions": count,
                        "weight_pct": as_float(Decimal(count) / Decimal(len(active)) * Decimal("100")),
                    }
                    for signal, count in sorted(signal_counts.items())
                    if active
                ],
            }
        )
        previous_session = on_or_before(market_bars, session)

    open_positions: list[dict[str, object]] = []
    for ticker, position in active.items():
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
                **fixed_changes_from_bars(charts[ticker], latest_market.day),
                "status": "open",
            }
        )

    simulated_trades: list[dict[str, object]] = []
    for position in [*cycles, *open_positions]:
        simulated_trades.append(
            {
                "date": position["entry_date"],
                "signal_observed_date": position["signal_observed_date"],
                "action": "buy",
                "ticker": position["ticker"],
                "entry_signal": position["entry_signal"],
                "execution_price": position["entry_price"],
                "quantity": as_float(Decimal(str(position["shares"]))),
                "usd_amount": as_float(VARIABLE_ENTRY_USD),
                "gain_loss": None,
            }
        )
    for position in cycles:
        simulated_trades.append(
            {
                "date": position["exit_date"],
                "signal_observed_date": position["exit_signal_observed_date"],
                "action": "sell",
                "ticker": position["ticker"],
                "entry_signal": position["entry_signal"],
                "execution_price": position["exit_price"],
                "quantity": as_float(Decimal(str(position["shares"]))),
                "usd_amount": position["ending_value"],
                "gain_loss": position["gain_loss"],
            }
        )
    simulated_trades.sort(key=lambda row: (row["date"], row["ticker"], row["action"]))

    latest_candidates = ranked_candidates(latest_market.day)
    latest_candidate_by_ticker = {str(row["ticker"]): row for row in latest_candidates}
    pending_sell_tickers = {
        ticker
        for ticker, position in active.items()
        if ticker not in latest_candidate_by_ticker
        and int(position.get("below_master_streak", 0)) + 1 >= 5
    }
    active_after_pending_sells = {
        ticker: position
        for ticker, position in active.items()
        if ticker not in pending_sell_tickers
    }
    latest_buys = fill_candidates(latest_candidates, active_after_pending_sells)
    pending_next_close_orders: list[dict[str, object]] = []
    for ticker, row in sorted(latest_buys.items()):
        pending_next_close_orders.append(
            {
                "date": "next available close",
                "signal_observed_date": latest_market.day.isoformat(),
                "action": "buy",
                "ticker": ticker,
                "entry_signal": row["entry_signal"],
                "execution_price": None,
                "quantity": None,
                "usd_amount": as_float(VARIABLE_ENTRY_USD),
                "gain_loss": None,
                "status": "pending",
                "master_score": as_float(Decimal(str(row["master_score"]))),
            }
        )
    for ticker in sorted(pending_sell_tickers):
        position = active[ticker]
        pending_next_close_orders.append(
            {
                "date": "next available close",
                "signal_observed_date": latest_market.day.isoformat(),
                "action": "sell",
                "ticker": ticker,
                "entry_signal": position["entry_signal"],
                "execution_price": None,
                "quantity": as_float(Decimal(str(position["shares"]))),
                "usd_amount": None,
                "gain_loss": None,
                "status": "pending",
            }
        )

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
    starting_deployed = Decimal(str(prior_series["deployed_capital"])) if prior_series else Decimal("0")
    ending_equity = Decimal(str(ending_series["value"]))
    ending_deployed = Decimal(str(ending_series["deployed_capital"]))
    period_basis = starting_equity + ending_deployed - starting_deployed
    period_gain = ending_equity - period_basis
    open_positions.sort(key=lambda row: row["return_pct"], reverse=True)
    realized_positions = sorted(cycles, key=lambda row: row["return_pct"], reverse=True)
    visible_series = [
        row for row in series if date.fromisoformat(str(row["date"])) >= selected_start
    ]
    visible_sector_exposure = [
        row for row in sector_exposure if date.fromisoformat(str(row["date"])) >= selected_start
    ]
    visible_signal_mix = [
        row for row in signal_mix if date.fromisoformat(str(row["date"])) >= selected_start
    ]
    invested_by_category: list[dict[str, object]] = []
    for category in ("fresh", "strict", "near"):
        closed = [cycle for cycle in cycles if cycle["entry_signal"] == category]
        open_rows = [position for position in open_positions if position["entry_signal"] == category]
        invested = VARIABLE_ENTRY_USD * (len(closed) + len(open_rows))
        ending_value = sum((Decimal(str(cycle["ending_value"])) for cycle in closed), Decimal("0")) + sum(
            (Decimal(str(position["current_value"])) for position in open_rows),
            Decimal("0"),
        )
        invested_by_category.append(
            {
                "category": category,
                "entries": len(closed) + len(open_rows),
                "closed_positions": len(closed),
                "open_positions": len(open_rows),
                "deployed_capital": as_float(invested),
                "ending_value": as_float(ending_value),
                "gain_loss": as_float(ending_value - invested),
                "return_pct": as_float(pct_change(ending_value, invested)),
            }
        )
    invested_by_category.sort(key=lambda row: row["return_pct"], reverse=True)

    detail = {
        "investor": MASTER_STRATEGY_NAME,
        "source": "derived-master-signal-strategy",
        "strategy_start": VARIABLE_STRATEGY_START.isoformat(),
        "from_date": selected_start.isoformat(),
        "to_date": latest_market.day.isoformat(),
        "initial_value": as_float(period_basis),
        "current_value": as_float(ending_equity),
        "gain_loss": as_float(period_gain),
        "return_pct": as_float(pct_change(ending_equity, period_basis)),
        **fixed_changes_from_series(series),
        "position_count": len(open_positions),
        "positions": open_positions,
        "realized_positions": realized_positions,
        "simulated_trades": simulated_trades,
        "pending_next_close_orders": pending_next_close_orders,
        "execution_convention": "Observe EOD signals and news after one close; execute the ranked rebalance at the next available EOD close.",
        "series": visible_series,
        "sector_exposure": visible_sector_exposure,
        "signal_mix": visible_signal_mix,
        "benchmark_comparison": benchmark_comparison(visible_series),
        "category_stats": invested_by_category,
        "category_stats_scope": f"{VARIABLE_STRATEGY_START.isoformat()} to {latest_market.day.isoformat()}",
        "trade_cycles": len(cycles) + len(open_positions),
        "closed_cycles": len(cycles),
        "news_counts_to_date": daily_news.get("to_date"),
        "position_limit": MASTER_POSITION_LIMIT,
        "sector_limit": MASTER_SECTOR_LIMIT,
        "note": (
            "Master ranked portfolio. Each day it scores the hybrid tracked-stock plus mass-change universe "
            "using signal strength, fresh/strict/near category, five-day relative strength, volume ratio, "
            "news activity/acceleration, and overextension penalties. It keeps active positions while they "
            "remain qualified, waits for five consecutive disqualified observations before selling, fills open slots with the highest-ranked names up to "
            f"{MASTER_POSITION_LIMIT} positions, allows no more than {MASTER_SECTOR_LIMIT} per sector, "
            "and deploys $1,000 per entry. Signals/news are observed after one close and traded at the next close."
        ),
    }
    return with_variable_fx_fees(detail) if apply_wealthsimple_fx_fees else detail


def master_portfolio_summary(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    detail = master_portfolio_detail(start, end, apply_wealthsimple_fx_fees)
    return {key: detail[key] for key in SUMMARY_KEYS} | {
        "warnings": [],
        "pending_next_close_orders": detail.get("pending_next_close_orders", []),
        "execution_convention": detail.get("execution_convention"),
    }


def mass_change_strategy_summary(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    detail = variable_strategy_detail(
        start,
        end,
        strategy_name=MASS_CHANGE_STRATEGY_NAME,
        more_signals_exit=True,
        universe_assets=mass_change_assets(),
        apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
    )
    return {
        key: detail[key]
        for key in SUMMARY_KEYS
    } | {"warnings": []}


def variable_more_signals_summary(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    detail = variable_strategy_detail(
        start,
        end,
        strategy_name=VARIABLE_MORE_SIGNALS_NAME,
        more_signals_exit=True,
        apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
    )
    return {
        key: detail[key]
        for key in SUMMARY_KEYS
    } | {"warnings": []}


def variable_technical_strategy_summary(
    strategy_name: str,
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    config = VARIABLE_TECHNICAL_STRATEGIES[strategy_name]
    detail = variable_strategy_detail(
        start,
        end,
        strategy_name=strategy_name,
        more_signals_exit=bool(config.get("more_signals_exit")),
        entry_categories=config.get("entry_categories"),
        apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
    )
    return {
        key: detail[key]
        for key in SUMMARY_KEYS
    } | {"warnings": []}


def variable_news_strategy_summary(
    strategy_name: str,
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    config = NEWS_STRATEGIES[strategy_name]
    detail = variable_strategy_detail(
        start,
        end,
        strategy_name=strategy_name,
        news_rule=str(config["rule"]),
        entry_categories=config.get("entry_categories"),
        entry_news_rule=str(config.get("entry_news_rule", "ignore")),
        apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        news_note=str(config["note"]),
    )
    summary = {
        key: detail[key]
        for key in SUMMARY_KEYS
    } | {"warnings": []}
    if strategy_name == "watchlist-variable-news-optimized-experimental":
        summary["pending_next_close_orders"] = detail.get("pending_next_close_orders", [])
        summary["execution_convention"] = detail.get("execution_convention")
    return summary


def hybrid_news_optimized_strategy_summary(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    config = NEWS_STRATEGIES["watchlist-variable-news-optimized-experimental"]
    detail = variable_strategy_detail(
        start,
        end,
        strategy_name=HYBRID_NEWS_OPTIMIZED_STRATEGY_NAME,
        news_rule=str(config["rule"]),
        entry_categories=config.get("entry_categories"),
        entry_news_rule=str(config.get("entry_news_rule", "ignore")),
        universe_assets=hybrid_news_optimized_assets(),
        apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        news_note=f"Expanded-universe version of {config['note']}",
    )
    return {
        key: detail[key]
        for key in SUMMARY_KEYS
    } | {"warnings": []}


def analysis_driven_strategy_detail(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    config = NEWS_STRATEGIES["watchlist-variable-news-optimized-experimental"]
    return variable_strategy_detail(
        start,
        end,
        strategy_name=ANALYSIS_DRIVEN_STRATEGY_NAME,
        news_rule=str(config["rule"]),
        entry_categories={"fresh", "strict"},
        entry_news_rule="accelerating",
        entry_analysis_rule="quality-score",
        apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        news_note=(
            "Buy fresh or strict signals only when seven-day Alpaca news is accelerating "
            f"and the market-analysis score is at least {as_float(ANALYSIS_ENTRY_SCORE)}. "
            "The score rewards relative strength, volume confirmation, trend quality, "
            "multi-horizon confirmation, and penalizes overextended moves. Exit rules "
            f"match {config['note']}"
        ),
    )


def analysis_driven_strategy_summary(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    detail = analysis_driven_strategy_detail(start, end, apply_wealthsimple_fx_fees)
    return {
        key: detail[key]
        for key in SUMMARY_KEYS
    } | {
        "warnings": [],
        "pending_next_close_orders": detail.get("pending_next_close_orders", []),
        "execution_convention": detail.get("execution_convention"),
    }


def variable_buy_only_detail(
    start: date,
    end: date | None,
    strategy_name: str = VARIABLE_BUY_ONLY_NAME,
    entry_category: str | None = None,
    apply_wealthsimple_fx_fees: bool = False,
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
    asset_types: dict[str, str] = {}
    for ticker, security_type in tracked_stock_assets():
        symbol = yahoo_symbol(ticker, security_type)
        try:
            _, bars = fetch_chart(symbol)
        except Exception:
            continue
        if bars:
            charts[ticker] = bars
            asset_types[ticker] = security_type

    positions: dict[str, dict[str, object]] = {}
    series: list[dict[str, object]] = []
    sector_exposure: list[dict[str, object]] = []
    signal_mix: list[dict[str, object]] = []
    previous_session = on_or_before(market_bars, VARIABLE_STRATEGY_START - timedelta(days=1))
    for session in sessions:
        if not previous_session:
            previous_session = on_or_before(market_bars, session - timedelta(days=1))
        for ticker, bars in charts.items():
            if ticker in positions:
                continue
            signal_bars = tuple(bar for bar in bars if bar.day <= previous_session.day)
            category = entry_signal(live_signal(signal_bars))
            if not category or (entry_category and category != entry_category):
                continue
            price_bar = on_or_before(bars, session)
            if not price_bar or price_bar.day <= previous_session.day:
                continue
            positions[ticker] = {
                "ticker": ticker,
                "entry_signal": category,
                "signal_observed_date": previous_session.day.isoformat(),
                "entry_date": price_bar.day.isoformat(),
                "entry_price": as_float(price_bar.close),
                "shares": VARIABLE_ENTRY_USD / price_bar.close,
                "initial_value": as_float(VARIABLE_ENTRY_USD),
            }
        deployed = VARIABLE_ENTRY_USD * len(positions)
        current = Decimal("0")
        sector_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for ticker, position in positions.items():
            price_bar = on_or_before(charts[ticker], session)
            if price_bar:
                position_value = Decimal(str(position["shares"])) * price_bar.close
                current += position_value
                sector, _ = sector_for_asset(
                    ticker,
                    asset_types.get(ticker, "stock"),
                    [strategy_name],
                )
                sector_values[sector] += position_value
        series.append(
            {
                "date": session.isoformat(),
                "value": as_float(current),
                "gain_loss": as_float(current - deployed),
                "deployed_capital": as_float(deployed),
                "active_positions": len(positions),
            }
        )
        sector_exposure.append(
            {
                "date": session.isoformat(),
                "sectors": [
                    {
                        "sector": sector,
                        "value": as_float(value),
                        "weight_pct": as_float(value / current * Decimal("100")),
                    }
                    for sector, value in sorted(sector_values.items())
                    if current
                ],
            }
        )
        signal_counts: defaultdict[str, int] = defaultdict(int)
        for position in positions.values():
            signal_counts[str(position.get("entry_signal") or "unknown")] += 1
        signal_mix.append(
            {
                "date": session.isoformat(),
                "signals": [
                    {
                        "signal": signal,
                        "positions": count,
                        "weight_pct": as_float(Decimal(count) / Decimal(len(positions)) * Decimal("100")),
                    }
                    for signal, count in sorted(signal_counts.items())
                    if positions
                ],
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
                **fixed_changes_from_bars(charts[ticker], latest_market.day),
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

    simulated_trades = sorted(
        (
            {
                "date": position["entry_date"],
                "signal_observed_date": position["signal_observed_date"],
                "action": "buy",
                "ticker": position["ticker"],
                "entry_signal": position["entry_signal"],
                "execution_price": position["entry_price"],
                "quantity": as_float(Decimal(str(position["shares"]))),
                "usd_amount": as_float(VARIABLE_ENTRY_USD),
                "gain_loss": None,
            }
            for position in open_positions
        ),
        key=lambda row: (row["date"], row["ticker"]),
    )

    pending_next_close_orders: list[dict[str, object]] = []
    for ticker, bars in sorted(charts.items()):
        if ticker in positions:
            continue
        signal_bars = tuple(bar for bar in bars if bar.day <= latest_market.day)
        category = entry_signal(live_signal(signal_bars))
        if not category or (entry_category and category != entry_category):
            continue
        pending_next_close_orders.append(
            {
                "date": "next available close",
                "signal_observed_date": latest_market.day.isoformat(),
                "action": "buy",
                "ticker": ticker,
                "entry_signal": category,
                "execution_price": None,
                "quantity": None,
                "usd_amount": as_float(VARIABLE_ENTRY_USD),
                "gain_loss": None,
                "status": "pending",
            }
        )

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
    visible_series = [
        row
        for row in series
        if date.fromisoformat(str(row["date"])) >= selected_start
    ]
    visible_sector_exposure = [
        row
        for row in sector_exposure
        if date.fromisoformat(str(row["date"])) >= selected_start
    ]
    visible_signal_mix = [
        row
        for row in signal_mix
        if date.fromisoformat(str(row["date"])) >= selected_start
    ]
    detail = {
        "investor": strategy_name,
        "source": "derived-buy-only-signal-strategy",
        "strategy_start": VARIABLE_STRATEGY_START.isoformat(),
        "from_date": selected_start.isoformat(),
        "to_date": latest_market.day.isoformat(),
        "initial_value": as_float(period_basis),
        "current_value": as_float(ending_equity),
        "gain_loss": as_float(period_gain),
        "return_pct": as_float(pct_change(ending_equity, period_basis)),
        **fixed_changes_from_series(series),
        "position_count": len(open_positions),
        "positions": open_positions,
        "simulated_trades": simulated_trades,
        "pending_next_close_orders": pending_next_close_orders,
        "execution_convention": "Observe EOD signals after one close; execute at the next available EOD close.",
        "series": visible_series,
        "sector_exposure": visible_sector_exposure,
        "signal_mix": visible_signal_mix,
        "benchmark_comparison": benchmark_comparison(visible_series),
        "category_stats": category_rows,
        "category_stats_scope": f"{VARIABLE_STRATEGY_START.isoformat()} to {latest_market.day.isoformat()}",
        "trade_cycles": len(open_positions),
        "closed_cycles": 0,
        "note": (
            "Buy-only EOD signal strategy. A stock is purchased once, at the next "
            f"available close after its first {entry_category or 'non-none'} signal, and is never sold. "
            "Each entry deploys $1,000. FX conversion is intentionally ignored."
        ),
    }
    return with_variable_fx_fees(detail) if apply_wealthsimple_fx_fees else detail


def variable_buy_only_summary(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    detail = variable_buy_only_detail(start, end, apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees)
    return {
        key: detail[key]
        for key in SUMMARY_KEYS
    } | {"warnings": []}


def variable_buy_only_category_summary(
    strategy_name: str,
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    detail = variable_buy_only_detail(
        start,
        end,
        strategy_name=strategy_name,
        entry_category=VARIABLE_BUY_ONLY_STRATEGIES[strategy_name],
        apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
    )
    return {
        key: detail[key]
        for key in SUMMARY_KEYS
    } | {"warnings": []}


def asset_summary(
    asset: tuple[str, str],
    owners: list[str],
    start: date,
    end: date | None,
) -> dict[str, object]:
    ticker, security_type = asset
    symbol = yahoo_symbol(ticker, security_type)
    sector, sector_source = sector_for_asset(ticker, security_type, owners)
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
            "sector": sector,
            "sector_source": sector_source,
            "currency": currency,
            "start_date": baseline.day.isoformat(),
            "end_date": latest.day.isoformat(),
            "start_price": as_float(baseline.close),
            "end_price": as_float(latest.close),
            "return_pct": as_float(pct_change(latest.close, baseline.close)),
            **fixed_changes_from_bars(bars, latest.day),
            "signal": live_signal(signal_bars),
            "wealthsimple": wealthsimple_metadata(ticker, security_type, symbol),
            "warning": None,
        }
    except Exception as exc:
        return {
            "ticker": ticker,
            "security_type": security_type,
            "yahoo_symbol": symbol,
            "owners": owners,
            "sector": sector,
            "sector_source": sector_source,
            "warning": str(exc),
            "signal": None,
            "wealthsimple": wealthsimple_metadata(ticker, security_type, symbol),
            **fixed_change_fields(Decimal("0"), Decimal("0"), Decimal("0")),
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


def nisarg_fixed_changes(end: date | None) -> dict[str, float]:
    return fixed_change_fields(Decimal("0"), Decimal("0"), Decimal("0"))


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
            **nisarg_fixed_changes(end),
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
            **fixed_change_fields(Decimal("0"), Decimal("0"), Decimal("0")),
            "position_count": 0,
            "source": "wealthsimple-import",
            "warnings": [str(exc)],
        }


def median_decimal(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal("2")


def business_dashboard_metrics(
    traders: list[dict[str, object]],
    stocks: list[dict[str, object]],
) -> dict[str, object]:
    valid_trader_returns = [Decimal(str(row["return_pct"])) for row in traders]
    valid_stock_rows = [row for row in stocks if not row.get("warning")]
    valid_stock_returns = [Decimal(str(row["return_pct"])) for row in valid_stock_rows]
    total_current = sum((Decimal(str(row["current_value"])) for row in traders), Decimal("0"))
    top_current = max((Decimal(str(row["current_value"])) for row in traders), default=Decimal("0"))
    signal_counts = {"fresh": 0, "strict": 0, "near": 0, "none": 0}
    for row in valid_stock_rows:
        signal = row.get("signal")
        if not isinstance(signal, dict) or signal.get("classification") == "none":
            signal_counts["none"] += 1
        elif signal.get("fresh_priority"):
            signal_counts["fresh"] += 1
        elif signal.get("classification") == "strict":
            signal_counts["strict"] += 1
        elif signal.get("classification") == "near":
            signal_counts["near"] += 1
        else:
            signal_counts["none"] += 1
    top_stock = max(valid_stock_rows, key=lambda row: row["return_pct"], default=None)
    bottom_stock = min(valid_stock_rows, key=lambda row: row["return_pct"], default=None)
    return {
        "portfolio_breadth": {
            "positive_count": sum(value > 0 for value in valid_trader_returns),
            "negative_count": sum(value < 0 for value in valid_trader_returns),
            "flat_count": sum(value == 0 for value in valid_trader_returns),
            "win_rate_pct": as_float(
                Decimal(sum(value > 0 for value in valid_trader_returns))
                / Decimal(len(valid_trader_returns))
                * 100
            )
            if valid_trader_returns
            else 0,
            "median_return_pct": as_float(median_decimal(valid_trader_returns)),
            "top_portfolio_concentration_pct": as_float(pct_change(top_current, total_current) + 100)
            if total_current
            else 0,
        },
        "stock_breadth": {
            "positive_count": sum(value > 0 for value in valid_stock_returns),
            "negative_count": sum(value < 0 for value in valid_stock_returns),
            "win_rate_pct": as_float(
                Decimal(sum(value > 0 for value in valid_stock_returns))
                / Decimal(len(valid_stock_returns))
                * 100
            )
            if valid_stock_returns
            else 0,
            "median_return_pct": as_float(median_decimal(valid_stock_returns)),
            "top_stock": top_stock["ticker"] if top_stock else None,
            "top_stock_return_pct": top_stock["return_pct"] if top_stock else 0,
            "bottom_stock": bottom_stock["ticker"] if bottom_stock else None,
            "bottom_stock_return_pct": bottom_stock["return_pct"] if bottom_stock else 0,
        },
        "signal_mix": signal_counts,
        "decision_flags": {
            "fresh_or_strict_count": signal_counts["fresh"] + signal_counts["strict"],
            "near_count": signal_counts["near"],
            "inactive_count": signal_counts["none"],
        },
    }


def signal_classification(row: dict[str, object]) -> str:
    signal = row.get("signal")
    if not isinstance(signal, dict) or signal.get("classification") == "none":
        return "none"
    if signal.get("fresh_priority"):
        return "fresh"
    classification = str(signal.get("classification") or "none")
    return classification if classification in {"strict", "near"} else "none"


def average_decimal(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0")) / Decimal(len(values)) if values else Decimal("0")


def sector_breakdowns(stocks: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in stocks:
        if row.get("warning"):
            continue
        grouped[str(row.get("sector") or "Unclassified")].append(row)

    breakdowns: list[dict[str, object]] = []
    for sector, rows in grouped.items():
        returns = [Decimal(str(row["return_pct"])) for row in rows]
        daily = [Decimal(str(row["daily_change_pct"])) for row in rows]
        five_day = [Decimal(str(row["five_day_change_pct"])) for row in rows]
        monthly = [Decimal(str(row["monthly_change_pct"])) for row in rows]
        signal_counts = {"fresh": 0, "strict": 0, "near": 0, "none": 0}
        for row in rows:
            signal_counts[signal_classification(row)] += 1
        top = max(rows, key=lambda row: row["return_pct"])
        bottom = min(rows, key=lambda row: row["return_pct"])
        breakdowns.append(
            {
                "sector": sector,
                "instrument_count": len(rows),
                "win_rate_pct": as_float(
                    Decimal(sum(value > 0 for value in returns))
                    / Decimal(len(returns))
                    * 100
                )
                if returns
                else 0,
                "average_return_pct": as_float(average_decimal(returns)),
                "median_return_pct": as_float(median_decimal(returns)),
                "daily_change_pct": as_float(average_decimal(daily)),
                "five_day_change_pct": as_float(average_decimal(five_day)),
                "monthly_change_pct": as_float(average_decimal(monthly)),
                "signal_counts": signal_counts,
                "top_ticker": top["ticker"],
                "top_return_pct": top["return_pct"],
                "bottom_ticker": bottom["ticker"],
                "bottom_return_pct": bottom["return_pct"],
                "tickers": sorted(str(row["ticker"]) for row in rows),
            }
        )
    breakdowns.sort(
        key=lambda row: (row["average_return_pct"], row["instrument_count"]),
        reverse=True,
    )
    for rank, row in enumerate(breakdowns, start=1):
        row["rank"] = rank
    return breakdowns


def build_overview(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
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
        lookback_parts: list[dict[str, Decimal]] = []
        warnings: list[str] = []
        for asset, amount in assets.items():
            if not amount:
                continue
            initial += amount
            row = indexed[asset]
            if row.get("warning"):
                current += amount
                lookback_parts.append(
                    {
                        "current": amount,
                        "daily": amount,
                        "five_day": amount,
                        "monthly": amount,
                    }
                )
                warnings.append(f"{asset[0]}: {row['warning']}")
            else:
                growth = Decimal(str(row["end_price"])) / Decimal(str(row["start_price"]))
                if row["currency"] == "CAD":
                    start_fx = on_or_after(fx_bars, date.fromisoformat(row["start_date"]))
                    end_fx = on_or_before(fx_bars, date.fromisoformat(row["end_date"]))
                    if not start_fx or not end_fx:
                        raise ValueError("missing CAD/USD exchange rate")
                    growth *= start_fx.close / end_fx.close
                elif apply_wealthsimple_fx_fees:
                    growth *= Decimal("1") - WEALTHSIMPLE_FX_FEE
                current_part = amount * growth
                current += current_part
                lookback_parts.append(
                    {
                        "current": current_part,
                        "daily": prior_value_from_return(current_part, row["daily_change_pct"]),
                        "five_day": prior_value_from_return(current_part, row["five_day_change_pct"]),
                        "monthly": prior_value_from_return(current_part, row["monthly_change_pct"]),
                    }
                )
        gain = current - initial
        traders.append(
            {
                "investor": investor,
                "initial_value": as_float(initial),
                "current_value": as_float(current),
                "gain_loss": as_float(gain),
                "return_pct": as_float(pct_change(current, initial)),
                **weighted_fixed_changes(lookback_parts),
                "position_count": sum(bool(amount) for amount in assets.values()),
                "source": "paper-ledger",
                "warnings": warnings,
            }
        )
    imported = nisarg_summary(start, end)
    if imported:
        traders.append(imported)
    traders.append(variable_strategy_summary(start, end, apply_wealthsimple_fx_fees))
    traders.append(master_portfolio_summary(start, end, apply_wealthsimple_fx_fees))
    traders.append(mass_change_strategy_summary(start, end, apply_wealthsimple_fx_fees))
    traders.append(variable_buy_only_summary(start, end, apply_wealthsimple_fx_fees))
    for strategy_name in VARIABLE_BUY_ONLY_STRATEGIES:
        traders.append(variable_buy_only_category_summary(strategy_name, start, end, apply_wealthsimple_fx_fees))
    traders.append(variable_more_signals_summary(start, end, apply_wealthsimple_fx_fees))
    for strategy_name in VARIABLE_TECHNICAL_STRATEGIES:
        traders.append(variable_technical_strategy_summary(strategy_name, start, end, apply_wealthsimple_fx_fees))
    for strategy_name in NEWS_STRATEGIES:
        traders.append(variable_news_strategy_summary(strategy_name, start, end, apply_wealthsimple_fx_fees))
    traders.append(hybrid_news_optimized_strategy_summary(start, end, apply_wealthsimple_fx_fees))
    traders.append(analysis_driven_strategy_summary(start, end, apply_wealthsimple_fx_fees))
    traders.extend(saved_strategy_dashboard_summaries(start, end, apply_wealthsimple_fx_fees))
    traders.sort(key=lambda row: row["return_pct"], reverse=True)
    for rank, trader in enumerate(traders, start=1):
        trader["rank"] = rank
    traders = [add_portfolio_priority(trader) for trader in traders]
    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat() if end else None,
        "latest_available_date": max(
            (row.get("end_date", "") for row in stocks if not row.get("warning")),
            default="",
        ),
        "traders": traders,
        "stocks": stocks,
        "sector_breakdowns": sector_breakdowns(stocks),
        "dashboard_metrics": business_dashboard_metrics(traders, stocks),
        "wealthsimple_fx_fees_enabled": apply_wealthsimple_fx_fees,
        "wealthsimple_fx_fee_rate": as_float(WEALTHSIMPLE_FX_FEE * 100),
        "wealthsimple_availability": {
            status: sum(
                row.get("wealthsimple", {}).get("availability") == status
                for row in stocks
            )
            for status in ("likely-supported", "verify-in-app", "likely-unsupported")
        },
    }


def build_eod_snapshot(apply_wealthsimple_fx_fees: bool = False) -> dict[str, object]:
    _, market_bars = fetch_chart("SPY")
    if len(market_bars) < 2:
        raise ValueError("missing market sessions for EOD snapshot")
    previous, latest = market_bars[-2:]
    overview = build_overview(previous.day, latest.day, apply_wealthsimple_fx_fees)
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


def paper_trader_detail(
    investor: str,
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
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
                spendable = (
                    amount * (Decimal("1") - WEALTHSIMPLE_FX_FEE)
                    if apply_wealthsimple_fx_fees
                    else amount
                )
                quantity = spendable / baseline.close
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
                    **fixed_changes_from_bars(bars, latest.day),
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
                    **fixed_change_fields(Decimal("0"), Decimal("0"), Decimal("0")),
                    "warning": str(exc),
                }
            )
    series_days = sorted(
        {
            bar.day
            for _, _, bars, _ in daily_parts
            for bar in bars
            if end is None or bar.day <= end
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
    fixed_changes = fixed_changes_from_series(series)
    positions.sort(key=lambda row: row["return_pct"], reverse=True)
    visible_series = [
        row
        for row in series
        if date.fromisoformat(str(row["date"])) >= start
    ]
    return {
        "investor": matched,
        "source": "paper-ledger",
        "initial_value": as_float(initial),
        "current_value": as_float(current),
        "gain_loss": as_float(current - initial),
        "return_pct": as_float(pct_change(current, initial)),
        **fixed_changes,
        "positions": positions,
        "series": visible_series,
        "benchmark_comparison": benchmark_comparison(visible_series),
        "wealthsimple_fx_fees_enabled": apply_wealthsimple_fx_fees,
    }


def paper_ledger_summaries(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for investor in allocations():
        detail = paper_trader_detail(
            investor,
            start,
            end,
            apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        )
        positions = list(detail.get("positions") or [])
        summaries.append(
            {
                key: detail[key]
                for key in SUMMARY_KEYS
                if key in detail
            }
            | {
                "position_count": len(positions),
                "source": "paper-ledger",
                "warnings": [
                    f"{row['ticker']}: {row['warning']}"
                    for row in positions
                    if row.get("warning")
                ],
            }
        )
    summaries.sort(key=lambda row: row["return_pct"], reverse=True)
    for rank, row in enumerate(summaries, start=1):
        row["rank"] = rank
    return [add_portfolio_priority(row) for row in summaries]


def nisarg_detail(start: date, end: date | None) -> dict[str, object]:
    from nisarg_window_return import calculate_window

    result = calculate_window(start, end)
    positions = [
        {
            "ticker": detail.ticker,
            "initial_value": as_float(detail.opening_value_usd),
            "current_value": as_float(detail.ending_value_usd),
            "gain_loss": as_float(detail.ending_value_usd - detail.opening_value_usd),
            **fixed_change_fields(Decimal("0"), Decimal("0"), Decimal("0")),
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
        **nisarg_fixed_changes(end),
        "positions": positions,
        "series": [],
        "warnings": result.warnings,
        "note": "Deposits, withdrawals, dividends, fees, interest, and FX cash movements are excluded.",
    }


def trader_detail(
    investor: str,
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    buy_only_category = VARIABLE_BUY_ONLY_STRATEGIES.get(investor.casefold())
    if buy_only_category:
        return variable_buy_only_detail(
            start,
            end,
            strategy_name=investor.casefold(),
            entry_category=buy_only_category,
            apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        )
    technical_strategy = VARIABLE_TECHNICAL_STRATEGIES.get(investor.casefold())
    if technical_strategy:
        return variable_strategy_detail(
            start,
            end,
            strategy_name=investor.casefold(),
            more_signals_exit=bool(technical_strategy.get("more_signals_exit")),
            entry_categories=technical_strategy.get("entry_categories"),
            apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        )
    news_strategy = NEWS_STRATEGIES.get(investor.casefold())
    if news_strategy:
        return variable_strategy_detail(
            start,
            end,
            strategy_name=investor.casefold(),
            news_rule=str(news_strategy["rule"]),
            entry_categories=news_strategy.get("entry_categories"),
            entry_news_rule=str(news_strategy.get("entry_news_rule", "ignore")),
            apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        )
    if investor.casefold() == VARIABLE_MORE_SIGNALS_NAME:
        return variable_strategy_detail(
            start,
            end,
            strategy_name=VARIABLE_MORE_SIGNALS_NAME,
            more_signals_exit=True,
            apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        )
    if investor.casefold() == VARIABLE_BUY_ONLY_NAME:
        return variable_buy_only_detail(start, end, apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees)
    if investor.casefold() == MASS_CHANGE_STRATEGY_NAME:
        return variable_strategy_detail(
            start,
            end,
            strategy_name=MASS_CHANGE_STRATEGY_NAME,
            more_signals_exit=True,
            universe_assets=mass_change_assets(),
            apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        )
    if investor.casefold() == HYBRID_NEWS_OPTIMIZED_STRATEGY_NAME:
        config = NEWS_STRATEGIES["watchlist-variable-news-optimized-experimental"]
        return variable_strategy_detail(
            start,
            end,
            strategy_name=HYBRID_NEWS_OPTIMIZED_STRATEGY_NAME,
            news_rule=str(config["rule"]),
            entry_categories=config.get("entry_categories"),
            entry_news_rule=str(config.get("entry_news_rule", "ignore")),
            universe_assets=hybrid_news_optimized_assets(),
            apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
            news_note=f"Expanded-universe version of {config['note']}",
        )
    if investor.casefold() == ANALYSIS_DRIVEN_STRATEGY_NAME:
        return analysis_driven_strategy_detail(
            start,
            end,
            apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        )
    if investor.casefold() == MASTER_STRATEGY_NAME:
        return master_portfolio_detail(
            start,
            end,
            apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
        )
    if investor.casefold() == VARIABLE_STRATEGY_NAME:
        return variable_strategy_detail(start, end, apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees)
    if investor.casefold() == "nisarg":
        if PUBLIC_DASHBOARD:
            raise KeyError(investor)
        return nisarg_detail(start, end)
    from backend.strategy_registry_service import read_strategies

    saved_strategy = next(
        (
            strategy
            for strategy in read_strategies(include_retired=False)
            if str(strategy["strategy_name"]).casefold() == investor.casefold()
            or str(strategy["strategy_id"]).casefold() == investor.casefold()
        ),
        None,
    )
    if saved_strategy:
        try:
            return saved_strategy_preview_detail(
                saved_strategy,
                start,
                end,
                apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
            )
        except ValueError as exc:
            raise KeyError(investor) from exc
    return paper_trader_detail(investor, start, end, apply_wealthsimple_fx_fees)
