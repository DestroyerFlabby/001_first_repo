# Wealth Automation: Allocation, Risk, And Rebalance Response

Date: 2026-06-12
From: Main Codex integration agent

## Status

`complete-for-phase`

Implemented a conservative Automated Wealth Review workflow that diagnoses allocation quality, risk readiness, and draft-only rebalance readiness.

## Implementation Summary

Added `automated_wealth_review_response`, exposed through `/api/wealth/automated-review`, and surfaced in the Wealth Overview as an advisor-style checklist.

The workflow returns:

- review status
- selected profile
- allocation health
- risk health
- rebalance health
- warnings
- assumptions
- read-only/no-order data-quality contract

## Automated Review Rules

### Data quality

Returns `data_quality_review_required` when:

- complete metadata coverage is below 75%, or
- asset-type coverage is below 90%.

### Allocation/rebalance

Returns `rebalance_review_required` when:

- explicit current policy-sleeve weights are supplied,
- metadata blockers are clear, and
- draft rebalance output has non-zero proposed dollar changes.

Returns `policy_profile_required` when:

- explicit current policy-sleeve weights are missing or invalid.

### Risk

Returns `risk_review_required` when supplied risk metrics show:

- current drawdown beyond 8%, or
- maximum drawdown beyond 12%, or
- risk alerts are present.

Risk detail is optional for this phase; missing risk detail is a warning, not an automatic breach.

## UI Integration

Added an Automated Review section to Wealth Overview:

- status card
- metadata coverage card
- concentration card
- draft rebalance availability card
- warnings and assumptions list
- Run Review button

The UI remains research-only and does not look like a trading bot.

## Example Current Output

Smoke test for `2026-01-31` to `2026-06-05` returned:

- HTTP 200
- status: `data_quality_review_required`
- next action: `Improve metadata coverage before relying on automation.`

This is expected because the automated review refuses to silently map incomplete metadata into policy sleeves.

## Files Changed

- `backend/automated_wealth_review_service.py`
- `backend/app.py`
- `frontend/index.html`
- `frontend/app.js`
- `tests/test_automated_wealth_review_service.py`

## Validation

- `python -m pytest PAPER_TRADING/tests/test_automated_wealth_review_service.py PAPER_TRADING/tests/test_strategy_selector_service.py -q`: 11 passed
- `python -m pytest PAPER_TRADING/tests -q`: 66 passed
- `python -m py_compile PAPER_TRADING/backend/app.py PAPER_TRADING/backend/automated_wealth_review_service.py PAPER_TRADING/backend/strategy_selector_service.py`: passed
- `node --check PAPER_TRADING/frontend/app.js`: passed
- FastAPI TestClient smoke:
  - `/api/wealth/strategy-selector`: 200
  - `/api/wealth/automated-review`: 200

## Follow-Up Recommendations

- Add explicit UI controls for current policy-sleeve weights if the user wants automated draft rebalancing directly from Wealth Overview.
- Keep the current conservative behavior: do not silently map unknown holdings to policy sleeves.
- Consider caching automated review output if allocation remains slow on Render.
