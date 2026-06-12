# Wealth Automation Strategy Review

Date: 2026-06-12
From: Listening wealth-management agent

## Status

`approved-with-notes`

The draft-only Strategy Selector / Investment Committee workflow is approved for this phase. The implementation uses a transparent risk-adjusted score, includes red-flag penalties, keeps output research-only, and does not create broker orders or ledger rows.

## Blocking Issues

None identified.

## Review Notes

- The scoring framework matches the requested intent: return and alpha matter, but drawdown, volatility, concentration, turnover, data quality, and scenario resilience all constrain the result.
- The red-flag penalty is directionally correct and addresses the key failure mode of raw-return chasing.
- The conservative draft blend keeps tactical sleeves bounded and preserves a majority core/policy allocation.
- Missing candidates are surfaced as warnings rather than breaking the workflow, which is the right behavior for this phase.

## Validation

Verified locally:

- `python -m pytest PAPER_TRADING\tests -q`: 60 passed.
- `node --check PAPER_TRADING\frontend\app.js`: passed.
- `python -m py_compile PAPER_TRADING\backend\app.py PAPER_TRADING\backend\strategy_selector_service.py`: passed.

The current validation is enough for this phase.

## Non-Blocking Follow-Ups

- Add caching if `/api/wealth/strategy-selector` becomes slow on full windows.
- Consider exposing score weights in the UI so the user can audit the ranking.
- Keep the recommendation language as “research candidate” or “review action,” not “best investment.”
- Proceed to `request-20260612-173328-wealth-auto-allocation-risk-rebalance.md`.
