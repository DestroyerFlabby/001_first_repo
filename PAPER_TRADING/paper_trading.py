from __future__ import annotations

import argparse
import csv
import sys
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path


TRADES_FILE = Path(__file__).parent / "data" / "trades.csv"
FIELDNAMES = [
    "trade_id",
    "timestamp",
    "investor",
    "ticker",
    "security_type",
    "side",
    "usd_amount",
    "amount_basis",
    "execution_price_usd",
    "price_basis",
    "notes",
]


@dataclass
class Position:
    shares: Decimal = Decimal("0")
    cost_basis: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")


def money(value: Decimal) -> str:
    return f"${value.quantize(Decimal('0.01')):,.2f}"


def shares(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):,}"


def decimal_arg(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(f"invalid decimal: {value}") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def trade_amount(args: argparse.Namespace) -> tuple[Decimal, str]:
    if args.usd_amount:
        return args.usd_amount, "reported"
    if args.security_type == "etf":
        return Decimal("2000"), "default-etf"
    return Decimal("1000"), f"default-{args.security_type}"


def read_trades() -> list[dict[str, str]]:
    with TRADES_FILE.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def calculate_positions(
    trades: list[dict[str, str]],
) -> tuple[dict[str, Position], list[str]]:
    positions: dict[str, Position] = {}
    warnings: list[str] = []

    for trade in trades:
        ticker = trade["ticker"]
        trade_id = trade["trade_id"]
        raw_price = trade["execution_price_usd"].strip()
        if not raw_price:
            warnings.append(f"{trade_id}: {ticker} has no price and is excluded")
            continue

        usd_amount = Decimal(trade["usd_amount"])
        price = Decimal(raw_price)
        trade_shares = usd_amount / price
        position = positions.setdefault(ticker, Position())

        if trade["side"] == "buy":
            position.shares += trade_shares
            position.cost_basis += usd_amount
            continue

        if trade_shares > position.shares:
            warnings.append(
                f"{trade_id}: {ticker} sell exceeds tracked shares and is excluded"
            )
            continue

        average_cost = position.cost_basis / position.shares
        removed_cost = average_cost * trade_shares
        position.shares -= trade_shares
        position.cost_basis -= removed_cost
        position.realized_pnl += usd_amount - removed_cost

    return positions, warnings


def investor_name(trade: dict[str, str]) -> str:
    return trade.get("investor", "").strip() or "Unassigned"


def trades_for_investor(
    trades: list[dict[str, str]], investor: str | None
) -> list[dict[str, str]]:
    if not investor:
        return trades
    return [
        trade
        for trade in trades
        if investor_name(trade).casefold() == investor.casefold()
    ]


def total_realized_pnl(positions: dict[str, Position]) -> Decimal:
    return sum((position.realized_pnl for position in positions.values()), Decimal("0"))


def total_open_cost(positions: dict[str, Position]) -> Decimal:
    return sum((position.cost_basis for position in positions.values()), Decimal("0"))


def add_trade(args: argparse.Namespace) -> int:
    usd_amount, amount_basis = trade_amount(args)
    row = {
        "trade_id": uuid.uuid4().hex[:12],
        "timestamp": args.timestamp,
        "investor": args.investor.strip(),
        "ticker": args.ticker.upper(),
        "security_type": args.security_type,
        "side": args.side,
        "usd_amount": str(usd_amount),
        "amount_basis": amount_basis,
        "execution_price_usd": str(args.execution_price or ""),
        "price_basis": args.price_basis,
        "notes": args.notes,
    }
    with TRADES_FILE.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writerow(row)
    print(
        f"Added {row['trade_id']}: {row['investor']} {row['side']} "
        f"{row['ticker']} for {money(usd_amount)} ({amount_basis})"
    )
    return 0


def report(args: argparse.Namespace) -> int:
    trades = trades_for_investor(read_trades(), args.investor)
    if args.investor:
        print(f"Investor: {args.investor}")
    print(f"Trades recorded: {len(trades)}")

    grouped_trades: dict[str, list[dict[str, str]]] = {}
    for trade in trades:
        grouped_trades.setdefault(investor_name(trade), []).append(trade)

    active_positions: list[tuple[str, str, Position]] = []
    warnings: list[str] = []
    for investor, investor_trades in sorted(grouped_trades.items()):
        positions, investor_warnings = calculate_positions(investor_trades)
        warnings.extend(f"{investor}: {warning}" for warning in investor_warnings)
        active_positions.extend(
            (investor, ticker, position)
            for ticker, position in sorted(positions.items())
            if position.shares or position.realized_pnl
        )

    if not active_positions:
        print("No priced positions recorded.")
    else:
        print("\nInvestor              Ticker  Shares          Open cost       Avg cost       Realized P/L")
        print("--------------------  ------  --------------  --------------  -------------  --------------")
        for investor, ticker, position in active_positions:
            average_cost = (
                position.cost_basis / position.shares
                if position.shares
                else Decimal("0")
            )
            print(
                f"{investor[:20]:<20}  {ticker:<6}  {shares(position.shares):>14}  "
                f"{money(position.cost_basis):>14}  {money(average_cost):>13}  "
                f"{money(position.realized_pnl):>14}"
            )

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- {warning}")
    return 0


def progress(args: argparse.Namespace) -> int:
    trades = sorted(
        trades_for_investor(read_trades(), args.investor),
        key=lambda trade: trade["timestamp"],
    )
    print(f"Investor: {args.investor}")
    print(f"Trades recorded: {len(trades)}")
    if not trades:
        return 0

    print("\nTimestamp                  Side  Ticker  Amount          Open cost       Realized P/L")
    print("-------------------------  ----  ------  --------------  --------------  --------------")
    processed: list[dict[str, str]] = []
    for trade in trades:
        processed.append(trade)
        positions, _ = calculate_positions(processed)
        print(
            f"{trade['timestamp']:<25}  {trade['side']:<4}  {trade['ticker']:<6}  "
            f"{money(Decimal(trade['usd_amount'])):>14}  "
            f"{money(total_open_cost(positions)):>14}  "
            f"{money(total_realized_pnl(positions)):>14}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track simulated USD paper trades.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add", help="Append one simulated trade.")
    add.add_argument("--timestamp", required=True, help="ISO-8601 timestamp with timezone.")
    add.add_argument("--investor", required=True)
    add.add_argument("--ticker", required=True)
    add.add_argument("--security-type", choices=["stock", "etf", "crypto"], required=True)
    add.add_argument("--side", choices=["buy", "sell"], required=True)
    add.add_argument("--usd-amount", type=decimal_arg)
    add.add_argument("--execution-price", type=decimal_arg)
    add.add_argument(
        "--price-basis",
        choices=["reported-fill", "alpaca-iex-minute-close", "alpaca-iex-eod-close", "pending"],
        default="pending",
    )
    add.add_argument("--notes", default="")
    add.set_defaults(func=add_trade)

    report_parser = subparsers.add_parser("report", help="Report open positions.")
    report_parser.add_argument("--investor", help="Limit the report to one investor.")
    report_parser.set_defaults(func=report)

    progress_parser = subparsers.add_parser(
        "progress", help="Show one investor's running trade history."
    )
    progress_parser.add_argument("--investor", required=True)
    progress_parser.set_defaults(func=progress)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "add" and bool(args.execution_price) == (args.price_basis == "pending"):
        print(
            "error: use price-basis=pending only when execution-price is omitted",
            file=sys.stderr,
        )
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
