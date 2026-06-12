# Phase 2 Assignment: Portfolio Scenario Testing

Date: 2026-06-12
Owner: Listening wealth-management agent
Integration owner: Main Codex agent

## Objective

Build a defensible, read-only scenario-analysis service for the existing `PAPER_TRADING` wealth dashboard. It must evaluate a supplied portfolio detail payload without writing trades, changing ledgers, or depending on another repository.

## Required scope

1. Add `PAPER_TRADING/backend/scenario_service.py`.
2. Add focused tests in `PAPER_TRADING/tests/test_scenario_service.py`.
3. Add concise methodology documentation under `PAPER_TRADING/research/wealth_management/`.
4. Do not edit `backend/app.py`, frontend files, or unrelated services; the integration owner will wire the API/UI.

## Contract

Expose a deterministic function similar to:

```python
scenario_response(portfolio_detail, *, base_currency="USD") -> dict
```

Use current holding weights from the supplied detail. Return:

- schema/calculation version, as-of date, base currency, assumptions, and data quality;
- portfolio-level estimated impact in percent and dollars for each scenario;
- position-level contribution for the largest affected holdings;
- at least these clearly labeled hypothetical shocks:
  - broad equity -20%;
  - technology/AI sector -30% with other equities -10%;
  - crypto -40%;
  - CAD strengthening 10% against USD for unhedged USD exposure;
  - concentration shock: largest position -35%;
- explicit warnings when sector, currency, asset type, value, or weight metadata is unavailable.

Use linear first-order shocks only and label them as estimates, not forecasts. Do not fabricate ETF look-through, derivatives convexity, taxes, trading costs, or liquidity effects. Unknown classifications must remain visible rather than silently assigned.

## Validation expectations

- deterministic output;
- contributions reconcile to portfolio scenario impact within a documented tolerance;
- sign conventions tested;
- missing/zero-value portfolio tested;
- weights normalized or warned about explicitly;
- no writes or order-generation behavior.

When complete, write `response-20260612-<time>-phase2-scenario-testing.md` in this folder summarizing files, assumptions, tests, and integration notes.
