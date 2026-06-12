# Phase 2 Correlation And Overlap Response

Date: 2026-06-12
Agent: Codex wealth-management implementation

## Files Changed

- `backend/correlation_service.py`
- `tests/test_correlation_service.py`
- `research/wealth_management/correlation_methodology.md`

No routes, frontend files, or existing services were edited.

## Contract

Portfolio correlation entry point:

```python
correlation_response(
    portfolio_detail: dict[str, object],
    start: date,
    end: date,
    *,
    price_loader: PriceLoader = default_price_loader,
    minimum_observations: int = 20,
) -> dict[str, object]
```

Direct ticker overlap entry point:

```python
direct_overlap_response(
    left_detail: dict[str, object],
    right_detail: dict[str, object],
) -> dict[str, object]
```

The correlation response includes schema/calculation versions, selected top positions, observation requirements, all pairwise results, average correlation, highest/lowest pairs, a diversification warning, missing-history warnings, assumptions, and source labels.

## Calculation Behavior

- Aggregates duplicate position rows by normalized ticker.
- Limits interactive analysis to the top 12 positions by current value, capping pair count at 66.
- Computes close-to-close simple returns.
- Aligns pairs only on dates present in both series; no filling or imputation.
- Requires 20 aligned observations by default.
- Returns unavailable state for insufficient history or zero variance.
- Warns when average valid correlation is at least 0.70 or at least half of valid pairs are 0.80 or higher.

Direct overlap sums the minimum portfolio weight for each shared ticker. ETF constituent look-through is explicitly unavailable and not implied.

## Validation

- `python -m pytest PAPER_TRADING\tests\test_correlation_service.py`: 6 passed.
- Python compilation passed.
- `git diff --check` passed for all assigned files.

Tests cover perfect positive/negative correlation, missing-date alignment, zero variance, insufficient history, top-12 limiting, direct overlap, and preserved data warnings.

## Performance Notes

- The default loader reuses `dashboard_service.fetch_chart` and symbol normalization.
- Production integration should run price loads through existing cache/background patterns rather than recomputing on every page render.
- The injected loader keeps unit tests deterministic and permits a cached production adapter later.

## Integration Instructions

1. Obtain the selected portfolio payload through existing `trader_detail` or model/rotation detail services.
2. Add a route that calls `correlation_response` for one selected portfolio and date window.
3. For comparisons, hydrate two details and call `direct_overlap_response` without additional market fetching.
4. Display unavailable pair reasons and data-quality warnings; do not substitute zero correlation.
5. Label overlap as direct ticker overlap and retain the ETF look-through limitation.
6. Run full merged tests and an endpoint smoke test after integration.
