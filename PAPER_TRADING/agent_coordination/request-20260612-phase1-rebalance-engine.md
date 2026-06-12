# Phase 1 Assignment: Draft-Only Rebalance Engine

Date: 2026-06-12
Scope: `PAPER_TRADING` only
Implementation authorized: yes

## Objective

Build a pure, testable rebalance calculation service. It must require explicit current allocations and compare them with an existing demo policy profile. It must never place or simulate broker orders automatically.

## Ownership

You may create/edit only:

- `backend/rebalance_service.py`
- `tests/test_rebalance_service.py`
- `research/wealth_management/rebalance_methodology.md`

Do not edit app routes, frontend files, or existing wealth services.

## Required Contract

Provide functions similar to:

```python
rebalance_preview(
    profile_id: str,
    current_allocations: list[dict[str, object]],
    portfolio_value: Decimal,
) -> dict[str, object]
```

Use `wealth_client_profiles.csv` and `wealth_model_allocations.csv` as policy inputs.

Requirements:

- Current allocations must be supplied explicitly by the caller.
- Validate current and target weights, duplicate baskets, unknown baskets, negative values, and totals.
- Use tolerance bands: default max of 2 percentage points absolute or 20% of target weight.
- Recommend the minimum policy-restoring trade toward the nearest acceptable boundary, not exact target, unless an explicit option requests exact target.
- Reserve or validate minimum cash where a cash sleeve is supplied; do not invent a cash holding.
- Return current, target, lower/upper band, drift, action, proposed weight, and proposed dollar change.
- Include estimated turnover and an explicit `draft_review_required` state.
- Include warnings that taxes, spreads, FX, fees, and tax lots are unavailable.
- No external writes, no trade ledger changes, and no broker calls.

## Tests

Cover overweight, underweight, within-band, invalid totals, duplicates, unknown profile, exact-target option, and dollar reconciliation.

## Response

Create `response-YYYYMMDD-HHMMSS-phase1-rebalance-engine.md` with files, contract, tests, limitations, and integration instructions.

