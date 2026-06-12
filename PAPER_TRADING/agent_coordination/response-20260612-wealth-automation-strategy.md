# Wealth Automation Strategy Response

Date: 2026-06-12
From: Main Codex integration agent

## Status

`complete-for-phase`

Implemented the draft-only Strategy Selector / Investment Committee workflow in `PAPER_TRADING`.

## Implementation Summary

Added a transparent risk-adjusted strategy comparison layer that ranks available research strategies and recommends one of:

- `hold_model`
- `prefer_blend`
- `prefer_rotation_research`
- `prefer_core_policy`
- `defer_insufficient_data`
- `manual_review_required`

The selector is research-only and does not create broker orders, ledger rows, or allocation changes.

## Files Changed

- `backend/strategy_selector_service.py`
- `backend/app.py`
- `frontend/index.html`
- `frontend/app.js`
- `tests/test_strategy_selector_service.py`

## Strategy Ranking Methodology

The score uses weighted components:

- 30% normalized return
- 20% normalized alpha versus benchmark
- 15% drawdown score
- 10% volatility score
- 10% concentration score
- 5% turnover score
- 5% data quality score
- 5% scenario resilience score

Then red-flag penalties are applied for:

- drawdown above 12% or 20%
- volatility above 30%
- top-five concentration above 60% or 70%
- fewer than five trades

This fixed an initial test failure where a high-return/high-drawdown strategy still ranked too highly.

## Candidate Strategies

The API currently attempts to compare:

- systematic model portfolio
- daily EOD rotation portfolio
- `watchlist-variable-news-optimized-experimental`
- `master-portfolio`
- `insta_watchlist`
- `social_media_signal`
- `model-portfolio`

Missing candidates are surfaced as warnings instead of failing the workflow.

## UI Integration

Added an Investment Committee section to Wealth Overview:

- recommendation cards
- ranked strategies table
- draft blend guardrails
- export button
- refresh button

The workflow lazy-loads when Wealth Overview is active.

## Example Current Output

Smoke test for `2026-01-31` to `2026-06-05` returned:

- HTTP 200
- recommendation status: `prefer_blend`
- recommended strategy: `watchlist-variable-news-optimized-experimental`
- candidates ranked: 4
- warnings: 5

## Validation

- `python -m pytest PAPER_TRADING/tests/test_strategy_selector_service.py -q`: 5 passed
- `python -m pytest PAPER_TRADING/tests -q`: 60 passed
- `python -m py_compile PAPER_TRADING/backend/app.py PAPER_TRADING/backend/strategy_selector_service.py`: passed
- `node --check PAPER_TRADING/frontend/app.js`: passed
- FastAPI TestClient smoke for `/api/wealth/strategy-selector`: passed

## Follow-Up Recommendations

- Cache selector output if real-window route latency becomes noticeable.
- Add more candidates only after their histories and execution conventions are reliable.
- Keep tactical blend sleeves capped and research-only.
- Proceed to the second request, `wealth-auto-allocation-risk-rebalance`, after review.
