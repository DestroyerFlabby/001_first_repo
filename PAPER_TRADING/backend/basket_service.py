from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path


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
