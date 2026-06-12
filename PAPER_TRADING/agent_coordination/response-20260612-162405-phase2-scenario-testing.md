# Phase 2 Scenario Testing Response

Date: 2026-06-12
Agent: Codex wealth-management implementation

## Files Changed

- `backend/scenario_service.py`
- `tests/test_scenario_service.py`
- `research/wealth_management/scenario_methodology.md`

No routes, frontend files, ledgers, or existing services were edited.

## Contract

```python
scenario_response(
    portfolio_detail: dict[str, object],
    *,
    base_currency: str = "USD",
) -> dict[str, object]
```

The response includes schema/calculation versions, portfolio/as-of metadata, base currency, normalized current value, five scenario results, assumptions, warnings, reconciliation tolerance, source labels, and explicit `read_only_no_orders` behavior.

Each scenario returns estimated percentage/dollar impact, affected-position count, the ten largest affected contributions, and contribution-reconciliation difference.

## Scenarios And Assumptions

- Broad equity -20% applies to stocks and ETFs explicitly classified as equity.
- Technology/AI equity -30%; other classified equity -10%.
- Explicit crypto exposure -40%.
- Explicit USD exposure -10% as a linear CAD-strengthening translation estimate.
- Largest positive current position -35%.

Current values are authoritative and weights are normalized from them. Inconsistent supplied weights generate a warning. Unknown asset type, sector, and currency remain unassigned to classification-dependent scenarios; they are never silently inferred.

The engine excludes ETF look-through, derivatives convexity, taxes, costs, liquidity, market impact, interactions, and rebalancing. Results are deterministic first-order estimates, not forecasts.

## Validation

- `python -m pytest PAPER_TRADING\tests\test_scenario_service.py`: 5 passed.
- Python compilation passed.
- `git diff --check` passed for all assigned files.

Tests cover expected signs and values for all shocks, contribution reconciliation, deterministic largest-position selection, missing metadata, zero-value portfolios, weight normalization warnings, and read-only behavior.

## Integration Notes

1. Hydrate a selected portfolio through an existing detail service and pass it directly to `scenario_response`.
2. Preserve warnings and assumptions in the UI; unknown classifications explain why a scenario may affect fewer holdings than expected.
3. Display these as hypothetical estimates, not projected losses or personalized recommendations.
4. Keep scenario output read-only and separate from rebalance/order workflows.
5. Run the merged suite and endpoint smoke test after adding API/UI integration.
