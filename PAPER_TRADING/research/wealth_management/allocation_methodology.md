# Allocation And Concentration Methodology

Date: 2026-06-12
Calculation version: `tracked-allocation-1.0`

## Scope

The allocation service describes a collection of unique primary tracked portfolio simulations. It is not a consolidated household balance sheet. Each portfolio has an independent simulated capital base, so portfolio values are summed only to compare the tracked research collection.

Shared securities across different portfolios are intentionally combined in the security view. This reveals overlap and concentration. Duplicate records for the same case-insensitive portfolio name are ignored.

## Included Values

- Only positive current position values are included.
- Values returned by existing dashboard detail services are treated as normalized to the dashboard reporting currency, currently USD.
- Missing sector, asset type, or currency remains in `Unknown / Unclassified`; unknown value is never redistributed.
- The runtime entry point selects portfolios marked `portfolio_group=primary` by the existing dashboard service.

Metadata is resolved field by field. Exact `asset_universe.csv` values take precedence. Blank fields may be supplemented only by deterministic mappings already used by the dashboard: position security type, `TSX_SYMBOLS` for CAD listings, `CRYPTO_SYMBOLS`, `TICKER_SECTOR_OVERRIDES`, and the existing unchanged-symbol convention for USD stock/ETF quotes. The service does not infer geography or ETF holdings.

If a position omits asset type, ticker-only universe metadata is accepted only when the ticker has exactly one universe record. Ambiguous tickers remain unknown.

## Calculations

For category value `V_i` and total included value `V`:

```text
weight_i = V_i / V
```

Security values are grouped by normalized ticker and asset type. Concentration measures are:

```text
top position = max(weight_i)
top five = sum(five largest security weights)
effective holdings = 1 / sum(weight_i^2)
```

The effective number of holdings decreases when value is concentrated even if the raw security count is high.

## Initial Alerts

- Single security above 10% of tracked value.
- One tracked portfolio above 25% of collection value.
- Classified sector above 35%.
- Classified currency above 80%.
- Complete sector/type/currency metadata below 95% of value.

Coverage reports complete classification plus separate asset-type, sector, and currency percentages. This distinguishes a genuinely unknown instrument from a known USD stock that lacks only a sector classification.

These are research review thresholds, not suitability conclusions or personalized advice. Future client-policy limits should be stored separately and applied by profile.

## Limitations

- Deposits, withdrawals, dividends, interest, taxes, and complete cash movements are not represented consistently.
- ETF holdings are not decomposed into underlying securities.
- Geography and account ownership are not reliable enough for this version.
- Summing independent simulations does not represent investable household wealth.
- Data freshness follows the selected dashboard close and underlying price-source availability.
