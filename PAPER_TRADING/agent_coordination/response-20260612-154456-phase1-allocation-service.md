# Phase 1 Allocation Service Response

Date: 2026-06-12
Agent: Codex wealth-management implementation

## Files Changed

- `backend/allocation_service.py`
- `tests/test_allocation_service.py`
- `research/wealth_management/allocation_methodology.md`

No shared integration files were edited.

## Contract

Primary runtime entry point:

```python
wealth_allocation_response(
    start: date,
    end: date,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]
```

The function uses `build_overview` to select unique portfolios marked `portfolio_group=primary`, hydrates them through `trader_detail`, and uses `read_asset_universe` for metadata. It returns:

- `schema_version`, `calculation_version`, `as_of`, `from_date`, and `base_currency`
- allocation by portfolio/strategy, sector, asset type, currency, and security
- included value, portfolio count, position-record count, and unique-security count
- top-position, top-five, and effective-number-of-holdings concentration measures
- explicit unknown/unclassified values and metadata coverage
- decision-oriented security, portfolio, sector, currency, and metadata alerts
- data freshness, warnings, assumptions, and source labels

The pure helper `build_allocation_response(...)` supports deterministic tests and future callers with precomputed details.

## Duplicate And Overlap Handling

- Duplicate portfolio records are ignored by case-insensitive portfolio name and reported as warnings.
- Shared securities across distinct portfolios are deliberately combined to reveal cross-portfolio overlap.
- The response identifies itself as `tracked_portfolio_research_collection`, not a household balance sheet.
- Unknown classifications remain in `Unknown / Unclassified` buckets and are not redistributed.

## Validation

- `python -m pytest PAPER_TRADING\tests\test_allocation_service.py`: 4 passed.
- Python compilation passed for the service and tests.
- `git diff --check` passed for all three assigned files.

Tests cover weight conservation, overlap aggregation, duplicate records, unknown metadata, effective holdings, concentration alerts, and empty input.

## Limitations

- Existing dashboard detail values are assumed to be normalized to USD.
- This aggregates independent tracked simulations and must not be presented as household net worth.
- ETF look-through, geography, account ownership, cash flows, taxes, dividends, and liabilities are not available reliably.
- The runtime path may remain market-data dependent because it intentionally reuses current dashboard services.

## Integration Instructions

1. Import `wealth_allocation_response` in `backend/app.py`.
2. Add an endpoint such as `/api/wealth-allocation` accepting the existing date-window and FX-fee parameters.
3. Render the response as a separate Allocation page or AI Wealth subsection; preserve the `view_note`, assumptions, warnings, and unknown buckets.
4. Do not merge these values into household totals or create broker orders.
5. Run the full merged test suite and an endpoint smoke test after integration.
