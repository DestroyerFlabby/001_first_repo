# Phase 2 Assignment: Correlation And Overlap Analytics

Date: 2026-06-12
Scope: `PAPER_TRADING` only
Implementation authorized: yes

## Objective

Build a reusable correlation and direct-overlap analytics service for one selected portfolio. The service should help distinguish a high security count from genuine diversification.

## Ownership

You may create/edit only:

- `backend/correlation_service.py`
- `tests/test_correlation_service.py`
- `research/wealth_management/correlation_methodology.md`

Do not edit app routes, frontend files, or existing services.

## Requirements

- Accept a portfolio detail payload with positions and a date window.
- Analyze at most the top 12 current positions by market value for interactive performance.
- Use aligned close-to-close returns with explicit minimum observations.
- Return pairwise correlations, average correlation, highest-correlation pairs, lowest-correlation pairs, and a diversification warning.
- Return direct ticker overlap helpers that can compare two portfolio detail payloads by current value/weight.
- Do not claim ETF look-through overlap; clearly mark it unavailable.
- Preserve missing-history warnings instead of filling returns.
- Keep market fetching injectable or isolate pure correlation helpers for deterministic tests.
- Include schema/calculation versions and data-quality metadata.

## Tests

Cover perfect positive/negative correlation, missing dates, zero-variance series, top-12 limiting, direct overlap, and insufficient history.

Create `response-YYYYMMDD-HHMMSS-phase2-correlation-overlap.md` with contract, tests, performance notes, and integration instructions.

