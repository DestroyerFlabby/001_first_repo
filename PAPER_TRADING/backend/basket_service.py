from __future__ import annotations

import csv
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from backend.dashboard_service import as_float, fetch_chart, on_or_before, pct_change, yahoo_symbol


ROOT = Path(__file__).resolve().parents[1]
BASKET_FILE = ROOT / "data" / "custom_baskets.csv"
BASKET_MEMBER_FILE = ROOT / "data" / "custom_basket_members.csv"
BASKET_FIELDS = [
    "basket_id",
    "basket_name",
    "status",
    "weighting_method",
    "rebalance_frequency",
    "benchmark",
    "created_at",
    "notes",
]
MEMBER_FIELDS = [
    "basket_id",
    "ticker",
    "asset_type",
    "target_weight",
    "source",
    "added_at",
    "notes",
]
VALID_STATUSES = {"research", "active", "archived"}
VALID_WEIGHTING = {"equal_weight", "custom_weight"}
VALID_REBALANCE = {"none", "monthly", "quarterly"}


def normalize_basket(row: dict[str, str], row_number: int) -> dict[str, object]:
    normalized = {field: (row.get(field) or "").strip() for field in BASKET_FIELDS}
    basket_id = normalized["basket_id"].casefold()
    status = normalized["status"].casefold()
    weighting = normalized["weighting_method"].casefold()
    rebalance = normalized["rebalance_frequency"].casefold()
    if not basket_id:
        raise ValueError(f"custom_baskets.csv row {row_number}: basket_id is required")
    if not normalized["basket_name"]:
        raise ValueError(f"custom_baskets.csv row {row_number}: basket_name is required")
    if status not in VALID_STATUSES:
        raise ValueError(f"custom_baskets.csv row {row_number}: invalid status '{status}'")
    if weighting not in VALID_WEIGHTING:
        raise ValueError(f"custom_baskets.csv row {row_number}: invalid weighting_method '{weighting}'")
    if rebalance not in VALID_REBALANCE:
        raise ValueError(f"custom_baskets.csv row {row_number}: invalid rebalance_frequency '{rebalance}'")
    normalized["basket_id"] = basket_id
    normalized["status"] = status
    normalized["weighting_method"] = weighting
    normalized["rebalance_frequency"] = rebalance
    return normalized


def normalize_member(row: dict[str, str], row_number: int) -> dict[str, object]:
    normalized = {field: (row.get(field) or "").strip() for field in MEMBER_FIELDS}
    basket_id = normalized["basket_id"].casefold()
    ticker = normalized["ticker"].upper()
    asset_type = normalized["asset_type"].casefold()
    if not basket_id:
        raise ValueError(f"custom_basket_members.csv row {row_number}: basket_id is required")
    if not ticker:
        raise ValueError(f"custom_basket_members.csv row {row_number}: ticker is required")
    if asset_type not in {"stock", "etf", "crypto"}:
        raise ValueError(f"custom_basket_members.csv row {row_number}: invalid asset_type '{asset_type}'")
    target_weight = normalized["target_weight"]
    if target_weight:
        try:
            if Decimal(target_weight) < 0:
                raise ValueError
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"custom_basket_members.csv row {row_number}: target_weight must be non-negative") from exc
    normalized["basket_id"] = basket_id
    normalized["ticker"] = ticker
    normalized["asset_type"] = asset_type
    return normalized


def read_csv(path: Path, fields: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            raise ValueError(f"{path.name} has unexpected columns")
        return list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def basket_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().casefold()).strip("-")
    return slug or "custom-basket"


def upsert_basket(payload: dict[str, object]) -> dict[str, object]:
    raw_name = str(payload.get("basket_name") or "").strip()
    basket_id = basket_slug(str(payload.get("basket_id") or raw_name))
    row = normalize_basket(
        {
            "basket_id": basket_id,
            "basket_name": raw_name,
            "status": str(payload.get("status") or "research"),
            "weighting_method": str(payload.get("weighting_method") or "equal_weight"),
            "rebalance_frequency": str(payload.get("rebalance_frequency") or "monthly"),
            "benchmark": str(payload.get("benchmark") or "SPY").strip().upper(),
            "created_at": str(payload.get("created_at") or date.today().isoformat()),
            "notes": str(payload.get("notes") or "").strip(),
        },
        0,
    )
    rows = read_csv(BASKET_FILE, BASKET_FIELDS)
    updated = False
    for index, existing in enumerate(rows):
        if str(existing.get("basket_id") or "").casefold() == basket_id:
            rows[index] = {field: str(row.get(field, "")) for field in BASKET_FIELDS}
            updated = True
            break
    if not updated:
        rows.append({field: str(row.get(field, "")) for field in BASKET_FIELDS})
    write_csv(BASKET_FILE, BASKET_FIELDS, rows)
    return row


def upsert_basket_member(basket_id: str, payload: dict[str, object]) -> dict[str, object]:
    basket_id = basket_slug(basket_id)
    baskets = custom_basket_response(include_archived=True)["baskets"]
    if not any(str(row["basket_id"]) == basket_id for row in baskets):
        raise KeyError(basket_id)
    row = normalize_member(
        {
            "basket_id": basket_id,
            "ticker": str(payload.get("ticker") or ""),
            "asset_type": str(payload.get("asset_type") or "stock"),
            "target_weight": str(payload.get("target_weight") or "").strip(),
            "source": str(payload.get("source") or "dashboard").strip(),
            "added_at": str(payload.get("added_at") or date.today().isoformat()),
            "notes": str(payload.get("notes") or "").strip(),
        },
        0,
    )
    rows = read_csv(BASKET_MEMBER_FILE, MEMBER_FIELDS)
    updated = False
    for index, existing in enumerate(rows):
        if (
            str(existing.get("basket_id") or "").casefold() == basket_id
            and str(existing.get("ticker") or "").upper() == str(row["ticker"])
            and str(existing.get("asset_type") or "").casefold() == str(row["asset_type"])
        ):
            rows[index] = {field: str(row.get(field, "")) for field in MEMBER_FIELDS}
            updated = True
            break
    if not updated:
        rows.append({field: str(row.get(field, "")) for field in MEMBER_FIELDS})
    write_csv(BASKET_MEMBER_FILE, MEMBER_FIELDS, rows)
    return row


def custom_basket_response(include_archived: bool = False) -> dict[str, object]:
    baskets = [
        normalize_basket(row, index)
        for index, row in enumerate(read_csv(BASKET_FILE, BASKET_FIELDS), start=2)
    ]
    members = [
        normalize_member(row, index)
        for index, row in enumerate(read_csv(BASKET_MEMBER_FILE, MEMBER_FIELDS), start=2)
    ]
    basket_ids = set()
    filtered_baskets: list[dict[str, object]] = []
    for basket in baskets:
        basket_id = str(basket["basket_id"])
        if basket_id in basket_ids:
            raise ValueError(f"custom_baskets.csv has duplicate basket_id: {basket_id}")
        basket_ids.add(basket_id)
        if basket["status"] == "archived" and not include_archived:
            continue
        filtered_baskets.append(basket)
    for member in members:
        if member["basket_id"] not in basket_ids:
            raise ValueError(f"custom_basket_members.csv references unknown basket_id: {member['basket_id']}")

    visible_ids = {str(row["basket_id"]) for row in filtered_baskets}
    visible_members = [member for member in members if str(member["basket_id"]) in visible_ids]
    member_counts = {
        basket_id: sum(str(member["basket_id"]) == basket_id for member in visible_members)
        for basket_id in visible_ids
    }
    enriched = [
        {
            **basket,
            "member_count": member_counts.get(str(basket["basket_id"]), 0),
            "members": [
                member
                for member in visible_members
                if str(member["basket_id"]) == str(basket["basket_id"])
            ],
        }
        for basket in filtered_baskets
    ]
    return {
        "baskets": sorted(enriched, key=lambda row: str(row["basket_id"])),
        "members": visible_members,
        "total": len(enriched),
        "statuses": sorted(VALID_STATUSES),
        "weighting_methods": sorted(VALID_WEIGHTING),
        "rebalance_frequencies": sorted(VALID_REBALANCE),
    }


def member_weight(member: dict[str, object], fallback_weight: Decimal) -> Decimal:
    value = str(member.get("target_weight") or "").strip()
    if not value:
        return fallback_weight
    return Decimal(value)


def basket_performance(
    basket_id: str,
    start: date,
    end: date | None,
) -> dict[str, object]:
    basket_id = basket_id.casefold()
    payload = custom_basket_response(include_archived=True)
    basket = next((row for row in payload["baskets"] if row["basket_id"] == basket_id), None)
    if not basket:
        raise KeyError(basket_id)
    members = list(basket["members"])
    if not members:
        return {
            "basket": basket,
            "from_date": start.isoformat(),
            "to_date": end.isoformat() if end else None,
            "return_pct": 0,
            "benchmark_return_pct": None,
            "alpha_pct": None,
            "members": [],
            "note": "Basket has no members.",
        }

    fallback_weight = Decimal("1") / Decimal(len(members))
    raw_weights = [member_weight(member, fallback_weight) for member in members]
    total_weight = sum(raw_weights, Decimal("0"))
    weights = [weight / total_weight for weight in raw_weights] if total_weight else [fallback_weight for _ in members]

    member_rows: list[dict[str, object]] = []
    basket_return = Decimal("0")
    effective_end: date | None = None
    for member, weight in zip(members, weights):
        ticker = str(member["ticker"])
        asset_type = str(member["asset_type"])
        symbol = yahoo_symbol(ticker, asset_type)
        try:
            _, bars = fetch_chart(symbol)
            start_bar = on_or_before(bars, start)
            end_bar = on_or_before(bars, end)
        except Exception as exc:
            member_rows.append(
                {
                    **member,
                    "weight_pct": as_float(weight * 100),
                    "return_pct": None,
                    "contribution_pct": None,
                    "warning": str(exc),
                }
            )
            continue
        if not start_bar or not end_bar:
            member_rows.append(
                {
                    **member,
                    "weight_pct": as_float(weight * 100),
                    "return_pct": None,
                    "contribution_pct": None,
                    "warning": "missing price window",
                }
            )
            continue
        effective_end = max(effective_end or end_bar.day, end_bar.day)
        member_return = pct_change(end_bar.close, start_bar.close)
        contribution = member_return * weight
        basket_return += contribution
        member_rows.append(
            {
                **member,
                "weight_pct": as_float(weight * 100),
                "start_price": as_float(start_bar.close),
                "end_price": as_float(end_bar.close),
                "start_date": start_bar.day.isoformat(),
                "end_date": end_bar.day.isoformat(),
                "return_pct": as_float(member_return),
                "contribution_pct": as_float(contribution),
                "warning": None,
            }
        )

    benchmark_return: Decimal | None = None
    benchmark = str(basket.get("benchmark") or "").strip()
    if benchmark:
        try:
            _, benchmark_bars = fetch_chart(benchmark)
            benchmark_start = on_or_before(benchmark_bars, start)
            benchmark_end = on_or_before(benchmark_bars, end)
            if benchmark_start and benchmark_end:
                benchmark_return = pct_change(benchmark_end.close, benchmark_start.close)
        except Exception:
            benchmark_return = None

    return {
        "basket": basket,
        "from_date": start.isoformat(),
        "to_date": effective_end.isoformat() if effective_end else (end.isoformat() if end else None),
        "return_pct": as_float(basket_return),
        "benchmark_return_pct": as_float(benchmark_return) if benchmark_return is not None else None,
        "alpha_pct": as_float(basket_return - benchmark_return) if benchmark_return is not None else None,
        "members": sorted(
            member_rows,
            key=lambda row: Decimal(str(row["contribution_pct"] if row["contribution_pct"] is not None else "-999999")),
            reverse=True,
        ),
        "note": "Window-return preview. Rebalance frequency is stored as metadata; this preview does not yet simulate monthly or quarterly rebalances.",
    }
