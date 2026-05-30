from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).parent
ACTIVITIES_FILE = ROOT / "data" / "wealthsimple_activities.csv"
IMPORTS_FILE = ROOT / "data" / "wealthsimple_imports.csv"
SOURCE_FIELDS = [
    "transaction_date",
    "settlement_date",
    "account_id",
    "account_type",
    "activity_type",
    "activity_sub_type",
    "direction",
    "symbol",
    "name",
    "currency",
    "quantity",
    "unit_price",
    "commission",
    "net_cash_amount",
]
ACTIVITY_FIELDS = [
    "activity_id",
    "owner",
    "source_file",
    "source_row",
    "duplicate_occurrence",
    *SOURCE_FIELDS,
]
IMPORT_FIELDS = [
    "imported_at_utc",
    "source_file",
    "owner",
    "export_as_of",
    "source_activity_rows",
    "new_activity_rows",
]


def decimal(value: str) -> Decimal:
    try:
        return Decimal(value or "0")
    except InvalidOperation:
        return Decimal("0")


def money(value: Decimal, currency: str) -> str:
    return f"{currency} {value.quantize(Decimal('0.01')):,.2f}"


def fingerprint(row: dict[str, str]) -> str:
    payload = "\x1f".join(row.get(field, "") for field in SOURCE_FIELDS)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def activity_id(row: dict[str, str], occurrence: int) -> str:
    return hashlib.sha256(f"{fingerprint(row)}:{occurrence}".encode("utf-8")).hexdigest()[:20]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def append_csv(path: Path, fields: list[str], row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def parse_export(path: Path) -> tuple[list[tuple[int, dict[str, str]]], str]:
    activities: list[tuple[int, dict[str, str]]] = []
    export_as_of = ""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in SOURCE_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"missing expected columns: {', '.join(missing)}")

        for source_row, raw_row in enumerate(reader, start=2):
            row = {field: (raw_row.get(field) or "").strip() for field in SOURCE_FIELDS}
            if row["transaction_date"].startswith("As of "):
                export_as_of = row["transaction_date"][len("As of ") :]
                continue
            if not row["transaction_date"] or not row["account_id"]:
                raise ValueError(f"malformed activity at source row {source_row}")
            activities.append((source_row, row))
    return activities, export_as_of


def import_export(args: argparse.Namespace) -> int:
    source = Path(args.file).resolve()
    source_rows, export_as_of = parse_export(source)
    existing = read_csv(ACTIVITIES_FILE)
    existing_ids = {row["activity_id"] for row in existing}
    occurrences: Counter[str] = Counter()
    new_rows: list[dict[str, str]] = []

    for source_row, row in source_rows:
        row_fingerprint = fingerprint(row)
        occurrences[row_fingerprint] += 1
        occurrence = occurrences[row_fingerprint]
        row_id = activity_id(row, occurrence)
        if row_id in existing_ids:
            continue
        new_rows.append(
            {
                "activity_id": row_id,
                "owner": args.owner,
                "source_file": source.name,
                "source_row": str(source_row),
                "duplicate_occurrence": str(occurrence),
                **row,
            }
        )
        existing_ids.add(row_id)

    all_rows = existing + new_rows
    all_rows.sort(key=lambda row: (row["transaction_date"], row["activity_id"]))
    write_csv(ACTIVITIES_FILE, ACTIVITY_FIELDS, all_rows)
    append_csv(
        IMPORTS_FILE,
        IMPORT_FIELDS,
        {
            "imported_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_file": source.name,
            "owner": args.owner,
            "export_as_of": export_as_of,
            "source_activity_rows": str(len(source_rows)),
            "new_activity_rows": str(len(new_rows)),
        },
    )
    print(f"Imported {len(new_rows)} new activities from {source.name}.")
    print(f"Tracked activities: {len(all_rows)}")
    if export_as_of:
        print(f"Export as of: {export_as_of}")
    return 0


def owner_rows(rows: list[dict[str, str]], owner: str | None) -> list[dict[str, str]]:
    if not owner:
        return rows
    return [row for row in rows if row["owner"].casefold() == owner.casefold()]


def summarize(args: argparse.Namespace) -> int:
    rows = owner_rows(read_csv(ACTIVITIES_FILE), args.owner)
    if not rows:
        print("No imported Wealthsimple activities found.")
        return 0

    dates = [row["transaction_date"] for row in rows]
    accounts = Counter((row["account_id"], row["account_type"]) for row in rows)
    activities = Counter(row["activity_type"] for row in rows)
    cash_by_currency: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    trade_cash_by_currency: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    dividends_by_currency: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    fees_by_currency: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    quantities: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))

    for row in rows:
        currency = row["currency"] or "N/A"
        cash = decimal(row["net_cash_amount"])
        cash_by_currency[currency] += cash
        if row["activity_type"] == "Trade":
            trade_cash_by_currency[currency] += cash
            quantities[(row["account_type"], row["symbol"], currency)] += decimal(row["quantity"])
        elif row["activity_type"] == "Dividend":
            dividends_by_currency[currency] += cash
        elif row["activity_type"] == "Fee":
            fees_by_currency[currency] += cash
        elif row["activity_type"] == "CryptoStakingReward":
            quantities[(row["account_type"], row["symbol"], currency)] += decimal(row["quantity"])

    print(f"Owner: {args.owner or 'all'}")
    print(f"Activities: {len(rows)}")
    print(f"Date range: {min(dates)} to {max(dates)}")
    print(f"Accounts: {len(accounts)}")
    print("\nAccount activity:")
    for (account_id, account_type), count in sorted(accounts.items(), key=lambda item: item[0][1]):
        print(f"- {account_type}: {account_id}: {count} activities")

    print("\nActivity types:")
    for activity_type, count in activities.most_common():
        print(f"- {activity_type}: {count}")

    print("\nNet cash amounts recorded:")
    for currency, value in sorted(cash_by_currency.items()):
        print(f"- {money(value, currency)}")

    print("\nTrade cash flow:")
    for currency, value in sorted(trade_cash_by_currency.items()):
        print(f"- {money(value, currency)}")

    print("\nDividends:")
    for currency, value in sorted(dividends_by_currency.items()):
        print(f"- {money(value, currency)}")

    print("\nFees:")
    for currency, value in sorted(fees_by_currency.items()):
        print(f"- {money(value, currency)}")

    open_quantities = [
        (key, value) for key, value in quantities.items() if value != Decimal("0") and key[1]
    ]
    print(f"\nDerived open symbol positions: {len(open_quantities)}")
    print("Use `positions` for the quantity-level view.")
    return 0


def positions(args: argparse.Namespace) -> int:
    rows = owner_rows(read_csv(ACTIVITIES_FILE), args.owner)
    quantities: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    names: dict[str, str] = {}
    for row in rows:
        if not row["symbol"]:
            continue
        names[row["symbol"]] = row["name"]
        if row["activity_type"] == "Trade":
            quantities[(row["account_type"], row["symbol"], row["currency"])] += decimal(
                row["quantity"]
            )
        elif row["activity_type"] == "CryptoStakingReward":
            quantities[(row["account_type"], row["symbol"], row["currency"])] += decimal(
                row["quantity"]
            )

    print("Account type          Symbol        Currency  Quantity")
    print("--------------------  ------------  --------  ----------------------")
    for (account_type, symbol, currency), quantity in sorted(quantities.items()):
        if quantity:
            print(f"{account_type:<20}  {symbol:<12}  {currency:<8}  {quantity}")
    return 0


def activities(args: argparse.Namespace) -> int:
    rows = owner_rows(read_csv(ACTIVITIES_FILE), args.owner)
    if args.account:
        rows = [row for row in rows if row["account_id"] == args.account]
    if args.symbol:
        rows = [row for row in rows if row["symbol"].casefold() == args.symbol.casefold()]
    if args.activity_type:
        rows = [
            row
            for row in rows
            if row["activity_type"].casefold() == args.activity_type.casefold()
        ]
    if args.date_from:
        rows = [row for row in rows if row["transaction_date"] >= args.date_from]
    if args.date_to:
        rows = [row for row in rows if row["transaction_date"] <= args.date_to]
    rows.sort(key=lambda row: (row["transaction_date"], row["activity_id"]))
    if args.limit:
        rows = rows[-args.limit :]

    print(
        "Date        Account type          Activity              Subtype         "
        "Symbol        Quantity          Unit price        Net cash"
    )
    print(
        "----------  --------------------  --------------------  --------------  "
        "------------  ----------------  ----------------  ----------------"
    )
    for row in rows:
        print(
            f"{row['transaction_date']:<10}  {row['account_type']:<20}  "
            f"{row['activity_type']:<20}  {row['activity_sub_type']:<14}  "
            f"{row['symbol']:<12}  {row['quantity']:<16}  {row['unit_price']:<16}  "
            f"{row['currency']} {row['net_cash_amount']}"
        )
    print(f"\nRows: {len(rows)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import and summarize Wealthsimple activities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import one Wealthsimple CSV export.")
    import_parser.add_argument("file")
    import_parser.add_argument("--owner", default="Nisarg")
    import_parser.set_defaults(func=import_export)

    summary_parser = subparsers.add_parser("summary", help="Show a high-level account summary.")
    summary_parser.add_argument("--owner")
    summary_parser.set_defaults(func=summarize)

    positions_parser = subparsers.add_parser("positions", help="Show derived symbol quantities.")
    positions_parser.add_argument("--owner")
    positions_parser.set_defaults(func=positions)

    activities_parser = subparsers.add_parser(
        "activities", help="Drill into imported row-level account activity."
    )
    activities_parser.add_argument("--owner")
    activities_parser.add_argument("--account")
    activities_parser.add_argument("--symbol")
    activities_parser.add_argument("--activity-type")
    activities_parser.add_argument("--date-from")
    activities_parser.add_argument("--date-to")
    activities_parser.add_argument("--limit", type=int, default=50)
    activities_parser.set_defaults(func=activities)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
