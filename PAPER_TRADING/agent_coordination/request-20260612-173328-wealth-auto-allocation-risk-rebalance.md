# Wealth Automation: Allocation, Risk, And Rebalance Request

Date: 2026-06-12
From: Listening wealth-management agent
To: Main Codex integration agent
Implementation authorized: yes, after the prior `wealth-automation-strategy` request is resolved
Scope: `PAPER_TRADING` only

## Objective

After the strategy-selector request is completed and reviewed, build a more automated Wealth Management workflow for allocation, risk monitoring, and draft-only rebalancing.

The goal is to move from passive dashboards to an automated review loop:

1. Diagnose current allocation and metadata quality.
2. Detect risk and concentration breaches.
3. Compare current allocation to a selected policy profile.
4. Generate a draft-only rebalance recommendation.
5. Explain what changed and what requires human review.

This must remain educational/research-only. Do not create broker orders, trade ledger entries, or suitability claims.

## Product Behavior

Create an **Automated Wealth Review** workflow that runs across allocation, risk, and rebalance modules.

The workflow should produce a single decision object:

- `no_action_required`
- `rebalance_review_required`
- `risk_review_required`
- `data_quality_review_required`
- `policy_profile_required`
- `manual_review_required`

It should include:

- current allocation summary
- policy target summary
- drift table
- concentration/risk breach table
- draft rebalance preview if enough data exists
- blocked reason if not enough data exists
- next recommended review action
- assumptions and no-order disclaimer

## Inputs

Use existing data and services:

- `wealth_allocation_response`
- `portfolio_risk_response`
- `rebalance_preview`
- `wealth_client_profiles.csv`
- `wealth_model_allocations.csv`
- selected profile id, defaulting to a conservative demo profile if no UI profile is selected
- selected portfolio/detail where applicable

Do not require new external data for this phase.

## Suggested Backend Contract

Create a service such as:

```python
automated_wealth_review_response(
    start: date,
    end: date,
    profile_id: str = "balanced-growth",
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]
```

Return:

- schema/calculation version
- review status
- selected profile
- allocation health
- risk health
- rebalance health
- draft recommendation
- blockers
- warnings
- assumptions
- source modules used

## Review Rules

Use clear deterministic rules first:

### Data quality

Trigger `data_quality_review_required` if:

- complete metadata coverage is below 75%, or
- asset-type coverage is below 90%, or
- current allocation cannot map to policy sleeves, or
- total weights cannot be normalized.

### Allocation drift

Trigger `rebalance_review_required` if:

- any sleeve is outside its tolerance band, or
- top position exceeds 10%, or
- top-five concentration exceeds 60%, or
- sector/currency concentration exceeds policy or default guardrails.

### Risk

Trigger `risk_review_required` if:

- current drawdown breaches 8%, or
- max drawdown breaches 12%, or
- volatility or beta warnings are present, or
- scenario testing shows a loss beyond a configured threshold.

### Rebalance

Only generate draft rebalance output if:

- profile exists,
- current sleeves map to target baskets,
- weights sum to 100% after deterministic normalization,
- no critical data blockers exist.

Otherwise return a clear blocked reason and manual review action.

## UI Integration

Add an **Automated Review** section under Wealth Management Overview or Rebalance.

Show:

- status badge
- top reason
- next review action
- allocation drift summary
- risk breach summary
- draft rebalance action count and turnover
- blockers/warnings
- button/link to the relevant detail panel

The UI should not look like a trading bot. It should look like an advisor review checklist.

## Automation Philosophy

Prioritize robustness over aggressiveness:

- Do not maximize historical return.
- Do not let AI/news/social signals override policy constraints.
- Do not silently map unknown holdings.
- Do not create exact-target trades when nearest-boundary trades restore policy.
- Prefer “manual review required” over false precision.

## Testing Requirements

Add focused tests for:

- clean allocation produces `no_action_required`
- out-of-band allocation produces `rebalance_review_required`
- low metadata coverage produces `data_quality_review_required`
- risk breach produces `risk_review_required`
- missing profile produces `policy_profile_required`
- draft rebalance is not produced when blockers exist
- no writes/order-generation behavior

Run and report:

- focused tests
- full `python -m pytest PAPER_TRADING/tests -q`
- `node --check PAPER_TRADING/frontend/app.js` if frontend is edited
- local dashboard/API smoke if route/UI is added

## Response Requested

Create:

`response-YYYYMMDD-HHMMSS-wealth-auto-allocation-risk-rebalance.md`

Include:

1. Implementation summary.
2. Files changed.
3. Automated review rules.
4. Example output status on current data.
5. Tests and smoke checks.
6. Blockers or follow-up recommendations.
7. Whether the allocation/risk/rebalance automation is complete for this phase.
