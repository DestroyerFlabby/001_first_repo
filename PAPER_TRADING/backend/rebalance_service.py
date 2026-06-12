from __future__ import annotations

from decimal import Decimal, InvalidOperation

from backend.wealth_operations_service import read_allocations, read_profiles


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"invalid numeric value: {value}") from exc


def rebalance_profiles_response() -> dict[str, object]:
    allocations = read_allocations()
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in allocations:
        grouped.setdefault(str(row["profile_id"]), []).append(row)
    return {
        "profiles": [
            {**profile, "target_allocations": grouped.get(str(profile["profile_id"]), [])}
            for profile in read_profiles(include_research=True)
        ],
        "execution_mode": "draft_review_only",
    }


def rebalance_preview(
    profile_id: str,
    current_allocations: list[dict[str, object]],
    portfolio_value: Decimal,
    *,
    exact_target: bool = False,
) -> dict[str, object]:
    profiles = {str(row["profile_id"]): row for row in read_profiles(include_research=True)}
    profile = profiles.get(profile_id.casefold())
    if not profile:
        raise ValueError(f"unknown profile: {profile_id}")
    if portfolio_value <= 0:
        raise ValueError("portfolio_value must be positive")
    targets = {
        str(row["basket_id"]): Decimal(str(row["target_weight"]))
        for row in read_allocations()
        if str(row["profile_id"]) == profile_id.casefold()
    }
    if not targets or sum(targets.values(), Decimal("0")) != Decimal("100"):
        raise ValueError("profile targets must exist and sum to 100%")

    current: dict[str, Decimal] = {}
    for row in current_allocations:
        basket = str(row.get("basket_id") or "").strip().casefold()
        if not basket:
            raise ValueError("current allocation is missing basket_id")
        if basket in current:
            raise ValueError(f"duplicate current allocation: {basket}")
        if basket not in targets:
            raise ValueError(f"basket is not allowed by profile: {basket}")
        weight = _decimal(row.get("current_weight"))
        if weight < 0:
            raise ValueError(f"negative current weight: {basket}")
        current[basket] = weight
    for basket in targets:
        current.setdefault(basket, Decimal("0"))
    if abs(sum(current.values(), Decimal("0")) - Decimal("100")) > Decimal("0.0001"):
        raise ValueError("current weights must sum to 100%")

    rows: dict[str, dict[str, Decimal | str]] = {}
    proposed: dict[str, Decimal] = {}
    for basket, target in targets.items():
        band = max(Decimal("2"), target * Decimal("0.20"))
        lower = max(Decimal("0"), target - band)
        upper = min(Decimal("100"), target + band)
        value = current[basket]
        if exact_target:
            next_weight = target
        elif value < lower:
            next_weight = lower
        elif value > upper:
            next_weight = upper
        else:
            next_weight = value
        proposed[basket] = next_weight
        rows[basket] = {"basket_id": basket, "current": value, "target": target, "lower": lower, "upper": upper}

    if not exact_target:
        imbalance = sum(proposed.values(), Decimal("0")) - Decimal("100")
        if imbalance > 0:
            donors = sorted(proposed, key=lambda basket: proposed[basket] - targets[basket], reverse=True)
            for basket in donors:
                capacity = proposed[basket] - Decimal(str(rows[basket]["lower"]))
                reduction = min(max(capacity, Decimal("0")), imbalance)
                proposed[basket] -= reduction
                imbalance -= reduction
                if imbalance <= Decimal("0.0000001"):
                    break
        elif imbalance < 0:
            need = -imbalance
            recipients = sorted(proposed, key=lambda basket: targets[basket] - proposed[basket], reverse=True)
            for basket in recipients:
                capacity = Decimal(str(rows[basket]["upper"])) - proposed[basket]
                addition = min(max(capacity, Decimal("0")), need)
                proposed[basket] += addition
                need -= addition
                if need <= Decimal("0.0000001"):
                    break

    if abs(sum(proposed.values(), Decimal("0")) - Decimal("100")) > Decimal("0.0001"):
        raise ValueError("unable to produce a self-financing rebalance within policy bands")

    output_rows: list[dict[str, object]] = []
    turnover = Decimal("0")
    for basket in targets:
        row = rows[basket]
        change = proposed[basket] - current[basket]
        turnover += abs(change)
        output_rows.append({
            "basket_id": basket,
            "current_weight_pct": float(current[basket]),
            "target_weight_pct": float(targets[basket]),
            "lower_band_pct": float(Decimal(str(row["lower"]))),
            "upper_band_pct": float(Decimal(str(row["upper"]))),
            "drift_pct": float(current[basket] - targets[basket]),
            "action": "buy" if change > Decimal("0.0001") else "sell" if change < Decimal("-0.0001") else "hold",
            "proposed_weight_pct": float(proposed[basket]),
            "proposed_dollar_change": float(change / Decimal("100") * portfolio_value),
        })
    output_rows.sort(key=lambda row: abs(float(row["proposed_dollar_change"])), reverse=True)
    return {
        "profile": profile,
        "portfolio_value": float(portfolio_value),
        "exact_target": exact_target,
        "status": "draft_review_required",
        "allocations": output_rows,
        "estimated_one_way_turnover_pct": float(turnover / Decimal("2")),
        "net_dollar_change": round(sum(float(row["proposed_dollar_change"]) for row in output_rows), 6),
        "warnings": [
            "Draft research preview only; no orders or ledger entries are created.",
            "Taxes, tax lots, bid/ask spreads, market impact, FX, commissions, and account restrictions are not included.",
            "Minimum cash policy cannot be verified unless cash is represented explicitly in the supplied current and target allocations.",
        ],
        "methodology": "Trade breaches toward the nearest policy boundary, then rebalance inside remaining bands to keep proposed weights self-financing.",
    }
