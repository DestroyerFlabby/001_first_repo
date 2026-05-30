from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


TRADES_FILE = Path(__file__).parent / "data" / "trades.csv"
EQUITY_START = date(2026, 1, 2)
CRYPTO_START = date(2026, 1, 1)
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


@dataclass
class PricePoint:
    day: date
    close: Decimal


@dataclass
class AssetResult:
    investor: str
    ticker: str
    amount: Decimal
    current_value: Decimal
    status: str


def money(value: Decimal) -> str:
    return f"${value.quantize(Decimal('0.01')):,.2f}"


def percent(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):+,.2f}%"


def fetch_daily_prices(symbol: str) -> tuple[str, list[PricePoint]]:
    period1 = int(datetime(2025, 12, 30, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.now(timezone.utc).timestamp()) + 86_400
    query = urlencode({"period1": period1, "period2": period2, "interval": "1d"})
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?{query}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=15) as response:
        result = json.load(response)["chart"]["result"][0]

    currency = result["meta"]["currency"]
    closes = result["indicators"]["quote"][0]["close"]
    prices = [
        PricePoint(datetime.fromtimestamp(timestamp, timezone.utc).date(), Decimal(str(close)))
        for timestamp, close in zip(result["timestamp"], closes)
        if close is not None
    ]
    return currency, prices


def price_on_or_after(prices: list[PricePoint], start: date) -> PricePoint | None:
    return next((price for price in prices if price.day >= start), None)


def yahoo_symbol(ticker: str, security_type: str) -> str:
    if security_type == "crypto":
        return CRYPTO_SYMBOLS[ticker]
    return TSX_SYMBOLS.get(ticker, ticker)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare simulated investor portfolios.")
    parser.add_argument(
        "--assets-for",
        help="Show ranked assets for one investor instead of portfolio totals.",
    )
    parser.add_argument("--limit", type=int, default=10)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    with TRADES_FILE.open(newline="", encoding="utf-8-sig") as handle:
        trades = list(csv.DictReader(handle))

    fx_currency, fx_prices = fetch_daily_prices("CAD=X")
    if fx_currency != "CAD":
        raise RuntimeError("unexpected CAD=X currency")
    initial_fx = price_on_or_after(fx_prices, EQUITY_START)
    latest_fx = fx_prices[-1]
    if not initial_fx:
        raise RuntimeError("missing initial CAD/USD exchange rate")

    cache: dict[str, tuple[str, list[PricePoint]]] = {}
    results: list[AssetResult] = []
    for trade in trades:
        if trade["side"] != "buy":
            continue
        ticker = trade["ticker"]
        security_type = trade["security_type"]
        amount = Decimal(trade["usd_amount"])
        symbol = yahoo_symbol(ticker, security_type)
        try:
            currency, prices = cache.setdefault(symbol, fetch_daily_prices(symbol))
            start = CRYPTO_START if security_type == "crypto" else EQUITY_START
            initial_price = price_on_or_after(prices, start)
            latest_price = prices[-1] if prices else None
            if not initial_price or not latest_price:
                raise ValueError("missing price history")

            if currency == "CAD":
                quantity = amount * initial_fx.close / initial_price.close
                current_value = quantity * latest_price.close / latest_fx.close
            elif currency == "USD":
                quantity = amount / initial_price.close
                current_value = quantity * latest_price.close
            else:
                raise ValueError(f"unsupported currency {currency}")
            status = f"{symbol}: {initial_price.day} to {latest_price.day}"
        except Exception as exc:
            current_value = amount
            status = f"held as cash: {symbol}: {exc}"
        results.append(AssetResult(trade["investor"], ticker, amount, current_value, status))

    totals: dict[str, tuple[Decimal, Decimal]] = defaultdict(lambda: (Decimal("0"), Decimal("0")))
    for result in results:
        invested, current = totals[result.investor]
        totals[result.investor] = (invested + result.amount, current + result.current_value)

    print(f"CAD/USD: {initial_fx.close} on {initial_fx.day} -> {latest_fx.close} on {latest_fx.day}")
    if args.assets_for:
        matching = [
            result
            for result in results
            if result.investor.casefold() == args.assets_for.casefold()
        ]
        matching.sort(key=lambda result: result.current_value / result.amount, reverse=True)
        print(f"\nInvestor: {args.assets_for}")
        print("Rank  Ticker        Initial         Current         Gain/Loss       Return")
        print("----  ------------  --------------  --------------  --------------  --------")
        for rank, result in enumerate(matching[: args.limit], start=1):
            gain = result.current_value - result.amount
            return_pct = gain / result.amount * 100
            print(
                f"{rank:>4}  {result.ticker:<12}  {money(result.amount):>14}  "
                f"{money(result.current_value):>14}  {money(gain):>14}  "
                f"{percent(return_pct):>8}"
            )
        return 0

    print("\nInvestor              Initial         Current         Gain/Loss       Return")
    print("--------------------  --------------  --------------  --------------  --------")
    ranking = sorted(
        totals.items(),
        key=lambda item: item[1][1] / item[1][0],
        reverse=True,
    )
    for investor, (initial, current) in ranking:
        gain = current - initial
        return_pct = gain / initial * 100
        print(
            f"{investor:<20}  {money(initial):>14}  {money(current):>14}  "
            f"{money(gain):>14}  {percent(return_pct):>8}"
        )

    cash_assets = [result for result in results if result.status.startswith("held as cash")]
    if cash_assets:
        print("\nHeld as cash because inception pricing was unavailable:")
        for result in cash_assets:
            print(f"- {result.investor}: {result.ticker}: {result.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
