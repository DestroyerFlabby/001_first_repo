# Phase 1 Follow-Up: Metadata Coverage Remediation

Date: 2026-06-12
Scope: `PAPER_TRADING` only
Implementation authorized: yes

## Finding

The real `/api/wealth/allocation` smoke test returned only 4.77% complete classification coverage across the primary tracked-portfolio research collection. Sector/type/currency must all be present for a value to count as complete.

## Assignment

Diagnose why coverage is low and improve reliable instrument metadata without inventing classifications.

You may edit only:

- `backend/allocation_service.py`
- `backend/universe_service.py` only if necessary and backward compatible
- `data/asset_universe.csv` only for deterministic corrections supported by existing repository mappings
- `tests/test_allocation_service.py`
- `research/wealth_management/allocation_methodology.md`

Do not edit frontend or `backend/app.py`.

Requirements:

- Distinguish genuinely missing metadata from mismatched ticker/type keys.
- Reuse reliable repository mappings such as `TSX_SYMBOLS`, crypto symbols, configured sectors, and asset types.
- Do not infer issuer geography or ETF look-through.
- Currency may be derived only from reliable exchange/symbol mappings already used by the application.
- Preserve explicit unknown buckets.
- Add field-level coverage percentages so sector, type, and currency can be assessed separately.
- Add tests for CAD-listed, USD-listed, crypto, and genuinely unknown instruments.
- Run the real allocation response if practical and report before/after coverage.

Create `response-YYYYMMDD-HHMMSS-phase1-metadata-coverage.md` with diagnosis, files changed, tests, and measured coverage.

