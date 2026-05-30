from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from compare_investors import (
    exchange_rate_for_day,
    fetch_daily_prices,
    price_on_or_after,
    price_on_or_before,
)


ACTIVITIES_FILE = Path(__file__).parent / "data" / "wealthsimple_activities.csv"
QUANTITY_ACTIVITY_TYPES = {
    "Trade",
    "CryptoStakingReward",
    "CorporateAction",
    "LegacyCorporateAction",
    "Correction",
    "InternalSecurityTransfer",
}
YAHOO_SYMBOLS = {
    "AAPL": "AAPL.NE",
    "ARTI": "ARTI.TO",
    "NVDA": "NVDA.NE",
    "QCN": "QCN.TO",
    "QUU": "QUU.TO",
    "RBNK": "RBNK.TO",
    "VIU": "VIU.TO",
    "XEQT": "XEQT.TO",
    "ZAG": "ZAG.TO",
    "ZCB": "ZCB.TO",
    "ZEA": "ZEA.TO",
    "ZFL": "ZFL.TO",
    "ZGLD": "ZGLD.TO",
    "ZHY": "ZHY.TO",
    "ZUAG.F": "ZUAG-F.TO",
    "BTC": "BTC-USD",
    "DOT": "DOT-USD",
    "ETH": "ETH-USD",
    # Wealthsimple's GOLD activity is a physically backed gold holding rather
    # than an exchange ticker. GC=F is used as a transparent valuation proxy.
    "GOLD": "GC=F",
}


@dataclass
class AssetDetail:
    ticker: str
    opening_quantity: Decimal
    ending_quantity: Decimal
    opening_value_usd: Decimal
    ending_value_usd: Decimal


@dataclass
class WindowResult:
    opening_value_usd: Decimal = Decimal("0")
    buys_usd: Decimal = Decimal("0")
    sales_usd: Decimal = Decimal("0")
    ending_value_usd: Decimal = Decimal("0")
    details: list[AssetDetail] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def deployed_capital_usd(self) -> Decimal:
        return self.opening_value_usd + self.buys_usd

    @property
    def ending_proceeds_and_value_usd(self) -> Decimal:
        return self.ending_value_usd + self.sales_usd

    @property
    def gain_usd(self) -> Decimal:
        return self.ending_proceeds_and_value_usd - self.deployed_capital_usd

    @property
    def return_pct(self) -> Decimal:
        if not self.deployed_capital_usd:
            return Decimal("0")
        return self.gain_usd / self.deployed_capital_usd * 100


def decimal(value: str) -> Decimal:
    return Decimal(value or "0")


def money(value: Decimal) -> str:
    return f"${value.quantize(Decimal('0.01')):,.2f}"


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from exc


def usd_value(
    value: Decimal,
    currency: str,
    day: date,
    fx_prices,
) -> Decimal:
    if currency == "USD":
        return value
    if currency != "CAD":
        raise ValueError(f"unsupported market currency {currency}")
    fx = exchange_rate_for_day(fx_prices, day)
    if not fx:
        raise ValueError(f"missing CAD/USD exchange rate for {day}")
    return value / fx.close


def calculate_window(
    start: date,
    end: date | None = None,
    owner: str = "Nisarg",
) -> WindowResult:
    with ACTIVITIES_FILE.open(newline="", encoding="utf-8-sig") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["owner"].casefold() == owner.casefold()
        ]

    opening_quantities: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    ending_quantities: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    window_trades: list[dict[str, str]] = []
    for row in rows:
        if not row["symbol"]:
            continue
        row_day = date.fromisoformat(row["transaction_date"])
        if row["activity_type"] in QUANTITY_ACTIVITY_TYPES:
            quantity = decimal(row["quantity"])
            if row_day <= start:
                opening_quantities[row["symbol"]] += quantity
            if end is None or row_day <= end:
                ending_quantities[row["symbol"]] += quantity
        if (
            row["activity_type"] == "Trade"
            and row_day > start
            and (end is None or row_day <= end)
        ):
            window_trades.append(row)

    _, fx_prices = fetch_daily_prices("CAD=X")
    latest_fx = price_on_or_before(fx_prices, end) if end else fx_prices[-1]
    if not latest_fx:
        raise ValueError("missing ending CAD/USD exchange rate")
    ending_day = latest_fx.day

    result = WindowResult()
    for trade in window_trades:
        cash_cad = decimal(trade["net_cash_amount"])
        trade_day = date.fromisoformat(trade["transaction_date"])
        cash_usd = usd_value(cash_cad, "CAD", trade_day, fx_prices)
        if trade["activity_sub_type"] == "BUY":
            result.buys_usd += -cash_usd
        elif trade["activity_sub_type"] == "SELL":
            result.sales_usd += cash_usd

    symbols = sorted(set(opening_quantities) | set(ending_quantities))
    for ticker in symbols:
        opening_quantity = opening_quantities[ticker]
        ending_quantity = ending_quantities[ticker]
        if not opening_quantity and not ending_quantity:
            continue
        yahoo_symbol = YAHOO_SYMBOLS.get(ticker, ticker)
        try:
            currency, prices = fetch_daily_prices(yahoo_symbol)
            opening_price = price_on_or_after(prices, start)
            ending_price = price_on_or_before(prices, end) if end else prices[-1]
            if not opening_price or not ending_price:
                raise ValueError("missing window prices")
            opening_value = usd_value(
                opening_quantity * opening_price.close,
                currency,
                opening_price.day,
                fx_prices,
            )
            ending_value = usd_value(
                ending_quantity * ending_price.close,
                currency,
                ending_price.day,
                fx_prices,
            )
        except Exception as exc:
            result.warnings.append(f"{ticker}: excluded from valuation: {exc}")
            continue
        result.opening_value_usd += opening_value
        result.ending_value_usd += ending_value
        result.details.append(
            AssetDetail(
                ticker,
                opening_quantity,
                ending_quantity,
                opening_value,
                ending_value,
            )
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calculate Nisarg's security-only Wealthsimple return over one window."
    )
    parser.add_argument("--from-date", type=parse_date, required=True)
    parser.add_argument("--to-date", type=parse_date)
    parser.add_argument("--owner", default="Nisarg")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.to_date and args.to_date < args.from_date:
        raise SystemExit("error: --to-date must be on or after --from-date")
    result = calculate_window(args.from_date, args.to_date, args.owner)
    ending = args.to_date.isoformat() if args.to_date else "latest available close"
    print(f"{args.owner} Wealthsimple security-only window: {args.from_date} -> {ending}")
    print(f"Opening holdings:                  {money(result.opening_value_usd)}")
    print(f"Security purchases after opening: {money(result.buys_usd)}")
    print(f"Final sale proceeds:               {money(result.sales_usd)}")
    print(f"Current unsold holdings:           {money(result.ending_value_usd)}")
    print(f"Gain/loss:                         {money(result.gain_usd)}")
    print(f"Simple return on deployed capital: {result.return_pct.quantize(Decimal('0.01')):+.2f}%")
    print("\nLargest holding changes:")
    for detail in sorted(
        result.details,
        key=lambda item: abs(item.ending_value_usd - item.opening_value_usd),
        reverse=True,
    )[:10]:
        change = detail.ending_value_usd - detail.opening_value_usd
        print(f"- {detail.ticker}: {money(change)}")
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"- {warning}")
    print("\nDeposits, withdrawals, dividends, interest, fees, and FX cash movements are excluded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
