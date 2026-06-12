# Portfolio Scenario Methodology

Date: 2026-06-12
Calculation version: `linear-scenarios-1.0`

## Purpose

The scenario service estimates how supplied current holdings would respond to defined instantaneous shocks. Results are educational first-order estimates, not forecasts, recommendations, or executable orders.

## Weighting And Contributions

Only positions with a ticker and positive current value are included. Weights are normalized from current values:

```text
weight_i = current_value_i / total_current_value
position impact_i = current_value_i * assigned_shock_i
portfolio impact % = sum(position impact_i) / total_current_value
```

Position percentage contributions must sum to the reported portfolio impact within `0.01` percentage points. Supplied weights are checked but current values remain authoritative; inconsistent supplied weights generate a warning.

## Hypothetical Shocks

- **Broad equity -20%:** stocks and ETFs explicitly classified as equity receive -20%.
- **Technology / AI -30%; other equity -10%:** classified technology/AI equity receives -30%; other classified equity receives -10%.
- **Crypto -40%:** positions explicitly typed or sectored as crypto receive -40%.
- **CAD strengthens 10% against USD:** positions explicitly denominated in USD receive a linear -10% translation shock in CAD-equivalent value.
- **Largest position -35%:** the largest positive current holding receives -35%.

Unknown asset type, sector, or currency remains visible and is not assigned to classification-dependent scenarios. The concentration shock needs only ticker and value.

## Exclusions

The service does not model ETF constituent look-through, derivative convexity, taxes, transaction costs, liquidity, market impact, active rebalancing, or interactions between shocks. It does not write files, modify ledgers, or generate orders.
