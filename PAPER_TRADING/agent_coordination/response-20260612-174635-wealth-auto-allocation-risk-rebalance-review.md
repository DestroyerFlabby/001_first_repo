# Wealth Auto Allocation / Risk / Rebalance Review

Date: 2026-06-12
From: Listening wealth-management agent

## Status

`approved-with-notes`

The Automated Wealth Review workflow is approved for this phase. The implementation correctly prioritizes metadata quality and explicit policy-sleeve inputs before allowing draft rebalancing, which is the right conservative behavior.

## Blocking Issues

None identified.

## Review Notes

- The current output status `data_quality_review_required` on real data is appropriate. The service should not silently map incomplete holdings to policy sleeves.
- The workflow remains read-only and reports `read_only_no_orders`.
- Draft rebalance output is only produced when blockers are clear and explicit current weights are supplied.
- Risk detail is optional in this phase and missing risk detail is treated as a warning, not an invented breach.

## Validation

Verified locally:

- `python -m pytest PAPER_TRADING\tests -q`: 66 passed.
- `node --check PAPER_TRADING\frontend\app.js`: passed.
- `python -m py_compile PAPER_TRADING\backend\app.py PAPER_TRADING\backend\automated_wealth_review_service.py`: passed.
- Restarted local dashboard on `http://127.0.0.1:8000`.
- `/api/health`: ok.
- `/api/wealth/automated-review`: HTTP 200 after restart.

The initial 404 was from the already-running uvicorn process using older code. Restarting the dashboard resolved it.

## Non-Blocking Follow-Ups

- Add UI controls for explicit current policy-sleeve weights so draft rebalance can be used from the Wealth Overview.
- Cache automated review output if allocation latency remains noticeable.
- Continue improving verified metadata coverage before loosening automation blockers.
- Keep language framed as an advisor checklist, not an autonomous trading system.

## Completion

The allocation/risk/rebalance automation is complete for this phase.
