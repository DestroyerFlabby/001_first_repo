from __future__ import annotations

import csv
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


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


def live_signal(bars: tuple[Bar, ...]) -> dict[str, object] | None:
    if len(bars) < 21:
        return None
    current = bars[-1]
    prior_5 = bars[-6:-1]
    prior_20 = bars[-21:-1]
    normal_volume = sum((bar.volume for bar in prior_20), Decimal("0")) / len(prior_20)
    if not normal_volume:
        return None
    volume_ratio = sum((bar.volume for bar in prior_5), Decimal("0")) / len(prior_5) / normal_volume
    return_pct = pct_change(current.close, prior_5[0].close)
    distance = pct_change(current.close, max(bar.close for bar in prior_20))
    strict = return_pct >= 10 and volume_ratio >= Decimal("1.5") and distance >= -2
    near = volume_ratio >= Decimal("1.25") and distance >= -2
    return {
        "as_of": current.day.isoformat(),
        "five_day_return_pct": as_float(return_pct),
        "five_day_volume_ratio": as_float(volume_ratio),
        "distance_to_20d_high_pct": as_float(distance),
        "classification": "strict" if strict else ("near" if near else "none"),
        "fresh_priority": bool(strict and return_pct <= 25),
    }


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
            "signal": live_signal(bars),
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
                current += amount * Decimal(str(row["end_price"])) / Decimal(str(row["start_price"]))
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
    if investor.casefold() == "nisarg":
        return nisarg_detail(start, end)
    return paper_trader_detail(investor, start, end)
