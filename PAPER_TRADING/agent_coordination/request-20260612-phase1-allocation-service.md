# Phase 1 Assignment: Allocation And Concentration Service

Date: 2026-06-12
Scope: `PAPER_TRADING` only
Implementation authorized: yes

## Objective

Implement a reusable allocation and concentration backend service using current repository data.

## Ownership

You may create and edit only:

- `backend/allocation_service.py`
- `tests/test_allocation_service.py`
- `research/wealth_management/allocation_methodology.md`

Do not edit shared integration files (`backend/app.py`, frontend files, or `dashboard_service.py`). The dashboard agent will integrate your service after review.

## Required Contract

Expose a function similar to:

```python
wealth_allocation_response(start: date, end: date, apply_wealthsimple_fx_fees: bool = False) -> dict[str, object]
```

Use existing dashboard/universe services rather than duplicating market fetching logic.

Return:

- `schema_version`, `calculation_version`, `as_of`, `base_currency`
- allocation by portfolio/strategy, sector, asset type, currency, and individual security where reliable
- total current value and included portfolio count
- top position concentration, top-five concentration, effective number of holdings
- metadata coverage and explicit unknown/unclassified buckets
- `data_quality` containing freshness, completeness, warnings, assumptions, and source labels
- decision-oriented concentration alerts

Avoid double-counting duplicate strategies or overlapping portfolios. Clearly define whether this is a collection of tracked portfolios or a consolidated household; default to a tracked-portfolio research view unless reliable household ownership data exists.

## Testing

Add focused unit tests for:

- weights sum to approximately 100%
- duplicate/unknown data handling
- effective holdings calculation
- concentration alerts
- empty input or missing metadata

Run your focused tests and report results.

## Response

Create `response-YYYYMMDD-HHMMSS-phase1-allocation-service.md` in this folder with files changed, contract summary, tests, limitations, and integration instructions.

