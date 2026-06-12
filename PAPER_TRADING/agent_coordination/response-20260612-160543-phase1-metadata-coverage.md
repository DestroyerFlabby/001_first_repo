# Phase 1 Metadata Coverage Response

Date: 2026-06-12
Agent: Codex wealth-management implementation

## Diagnosis

The 4.77% complete-coverage result was caused by two separate conditions:

1. Most primary portfolio position records contain ticker and current value but do not carry sector or currency. Many strategy positions do carry `security_type`.
2. `asset_universe.csv` contains the relevant ticker/type rows in many cases, but numerous seeded rows have blank sector/currency. Some imported Wealthsimple positions omit asset type entirely, so exact `(ticker, type)` lookup cannot match them.

This was not mainly ticker formatting. It was field incompleteness plus missing-type key shape.

## Files Changed

- `backend/allocation_service.py`
- `tests/test_allocation_service.py`
- `research/wealth_management/allocation_methodology.md`

No frontend, API integration, dashboard-service, universe-service, or CSV data files were edited.

## Remediation

- Resolve metadata field by field rather than treating one blank field as a failed record.
- Preserve exact `asset_universe.csv` values as first priority.
- Reuse position security type when present.
- Use `TICKER_SECTOR_OVERRIDES`, generic configured crypto/ETF sectors, `TSX_SYMBOLS`, `CRYPTO_SYMBOLS`, exchange metadata, and the dashboard's existing unchanged-symbol USD convention.
- Add ticker-only universe fallback only when the ticker has exactly one unambiguous universe row.
- Preserve `Unknown / Unclassified` for genuinely unresolved fields.
- Add separate asset-type, sector, currency, and complete-value coverage percentages.

No geography or ETF look-through was inferred.

## Measured Coverage

Real service run for 2026-01-31 through 2026-06-11, 13 primary portfolios, 159 unique securities:

| Measure | Before | After |
|---|---:|---:|
| Complete sector/type/currency | 4.77% | 57.41% |
| Asset type | not reported | 86.04% |
| Sector | not reported | 57.91% |
| Currency | not reported | 86.04% |

The remaining gap is explicit and legitimate under the no-invention constraint. Large unresolved imported positions lack asset type in their detail contract, and many stock rows lack a configured sector. Examples include imported ETFs/crypto aliases and stocks with no repository sector mapping. Raising coverage further requires verified instrument metadata or enriching the upstream imported-position contract.

## Tests And Checks

- `python -m pytest PAPER_TRADING\tests\test_allocation_service.py`: 7 passed.
- Python compilation passed.
- `git diff --check` passed for assigned files.

Coverage includes tests for CAD-listed securities, USD-listed securities, crypto, genuinely unknown instruments, unambiguous ticker-only metadata, and separate field-level coverage.

## Integration Notes

The existing `/api/wealth/allocation` integration can consume the expanded `metadata_coverage` object without changing prior fields. The dashboard should display field-level coverage and retain the complete-coverage warning until verified sector/type metadata improves.
