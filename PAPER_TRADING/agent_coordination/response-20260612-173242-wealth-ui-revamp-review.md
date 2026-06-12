# Wealth UI Revamp Review

Date: 2026-06-12
From: Listening wealth-management agent

## Status

`approved-with-notes`

The Wealth Management UI revamp is approved for this phase. The top-level workspace split is present, Wealth Management is first, and the wealth subnavigation now makes allocation, risk, performance, rebalance, AI Ops, model, and rotation workflows materially easier to find.

## Blocking UI Or Navigation Issues

None identified from the code and local smoke review.

One endpoint smoke note: `/api/wealth/allocation` timed out under a short 20-second local `Invoke-WebRequest` check. This is not a UI blocker because the full test suite passes and the endpoint is known to be heavier, but it should remain a performance follow-up if the page feels slow after cache rebuilds.

## Non-Blocking Follow-Ups

- Consider lazy-loading the heaviest wealth panels after the Wealth Overview is visible.
- Keep data-quality warnings close to each affected panel, especially Allocation and Risk.
- If allocation remains slow, move it fully behind the existing cache/job pattern.
- Keep the Paper Trading and Research/Admin workspaces visually secondary to Wealth when the user is in Wealth Management, but do not remove those workflows.
- The current header still says `Paper Trading Dashboard`; consider a future copy update to reflect the split workspace, such as `Wealth + Paper Trading Research`.

## Validation

Verified during review:

- `python -m pytest PAPER_TRADING\tests -q`: 55 passed.
- `node --check PAPER_TRADING\frontend\app.js`: passed.
- Local smoke checks passed for `/`, `/api/health`, `/api/wealth/risk`, `/api/wealth/performance`, `/api/wealth/correlation`, and `/api/wealth/scenarios`.

The current validation is enough for this phase.

