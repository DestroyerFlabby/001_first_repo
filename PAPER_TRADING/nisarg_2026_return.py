from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ACTIVITIES_FILE = Path(__file__).parent / "data" / "wealthsimple_activities.csv"
START = date(2026, 1, 2)
TSX_SYMBOLS = {
    "AAPL": "AAPL.NE",
    "ARTI": "ARTI.TO",
    "CASH": "CASH.TO",
    "NVDA": "NVDA.NE",
    "QCN": "QCN.TO",
    "QUU": "QUU.TO",
    "RBNK": "RBNK.TO",
    "VIU": "VIU.TO",
    "XEQT": "XEQT.TO",
    "ZAG": "ZAG.TO",
    "ZCB": "ZCB.TO",
    "ZEA": "ZEA.TO",
    "ZGLD": "ZGLD.TO",
    "ZHY": "ZHY.TO",
    "ZUAG.F": "ZUAG-F.TO",
}


@dataclass
class PricePoint:
    day: date
    close: Decimal


def decimal(value: str) -> Decimal:
    return Decimal(value or "0")


def money(value: Decimal) -> str:
    return f"CAD {value.quantize(Decimal('0.01')):,.2f}"


def fetch_prices(symbol: str) -> tuple[str, list[PricePoint]]:
    period1 = int(datetime(2025, 12, 30, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.now(timezone.utc).timestamp()) + 86_400
    query = urlencode({"period1": period1, "period2": period2, "interval": "1d"})
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?{query}"
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as response:
        result = json.load(response)["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    prices = [
        PricePoint(datetime.fromtimestamp(timestamp, timezone.utc).date(), Decimal(str(close)))
        for timestamp, close in zip(result["timestamp"], closes)
        if close is not None
    ]
    return result["meta"]["currency"], prices


def on_or_after(prices: list[PricePoint], start: date) -> PricePoint:
    return next(price for price in prices if price.day >= start)


def cad_value(price: Decimal, currency: str, cad_per_usd: Decimal) -> Decimal:
    return price * cad_per_usd if currency == "USD" else price


def main() -> int:
    with ACTIVITIES_FILE.open(newline="", encoding="utf-8-sig") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["owner"] == "Nisarg"
            and row["transaction_date"] >= "2026-01-01"
            and row["activity_type"] == "Trade"
        ]

    trades: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        trades[row["symbol"]].append(row)

    _, fx_prices = fetch_prices("CAD=X")
    start_fx = on_or_after(fx_prices, START)
    latest_fx = fx_prices[-1]
    total_opening = Decimal("0")
    total_buys = Decimal("0")
    total_sales = Decimal("0")
    total_current = Decimal("0")
    details = []

    for ticker, ticker_trades in sorted(trades.items()):
        running_quantity = Decimal("0")
        minimum_quantity = Decimal("0")
        buys = Decimal("0")
        sales = Decimal("0")
        for trade in sorted(ticker_trades, key=lambda row: (row["transaction_date"], row["activity_id"])):
            running_quantity += decimal(trade["quantity"])
            minimum_quantity = min(minimum_quantity, running_quantity)
            if trade["activity_sub_type"] == "BUY":
                buys += -decimal(trade["net_cash_amount"])
            elif trade["activity_sub_type"] == "SELL":
                sales += decimal(trade["net_cash_amount"])

        opening_quantity = -minimum_quantity
        current_quantity = opening_quantity + running_quantity
        yahoo_symbol = TSX_SYMBOLS.get(ticker, ticker)
        if ticker == "GOLD":
            yahoo_symbol = "GC=F"
        currency, prices = fetch_prices(yahoo_symbol)
        start_price = on_or_after(prices, START)
        latest_price = prices[-1]
        opening_value = opening_quantity * cad_value(start_price.close, currency, start_fx.close)
        current_value = current_quantity * cad_value(latest_price.close, currency, latest_fx.close)
        profit = current_value + sales - opening_value - buys
        details.append((ticker, profit, opening_value, buys, sales, current_value))
        total_opening += opening_value
        total_buys += buys
        total_sales += sales
        total_current += current_value

    invested = total_opening + total_buys
    profit = total_current + total_sales - invested
    return_pct = profit / invested * 100
    print("Nisarg 2026 traded-securities sleeve")
    print(f"Opening holdings required for 2026 sales: {money(total_opening)}")
    print(f"2026 security purchases:                  {money(total_buys)}")
    print(f"2026 final sale proceeds:                 {money(total_sales)}")
    print(f"Current value of unsold quantities:       {money(total_current)}")
    print(f"Gain/loss:                                {money(profit)}")
    print(f"Simple return on deployed capital:        {return_pct.quantize(Decimal('0.01')):+.2f}%")
    print("\nLargest gain/loss contributors:")
    for ticker, asset_profit, *_ in sorted(details, key=lambda item: abs(item[1]), reverse=True)[:10]:
        print(f"- {ticker}: {money(asset_profit)}")
    print(f"\nLatest market data date: {latest_fx.day}")
    print("Deposits, withdrawals, dividends, interest, fees, and FX exchanges are excluded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
