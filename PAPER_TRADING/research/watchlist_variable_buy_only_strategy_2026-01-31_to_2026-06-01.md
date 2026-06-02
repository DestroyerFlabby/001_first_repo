# Watchlist Variable Buy-Only Strategy: January 31, 2026 to June 1, 2026

Research snapshot generated: 2026-06-01

## Strategy Convention

- Dashboard trader name: `watchlist-variable-buy-only`
- Strategy inception: `2026-01-31`
- Universe: the currently tracked `stock` symbols in `data/trades.csv`,
  evaluated historically from strategy inception
- Eligible first-entry signals: `fresh`, `strict`, and `near`
- Execution convention: observe the EOD signal and buy at the next available
  market close to avoid using future information
- Entry amount: `$1,000` per stock
- Exit convention: never sell
- Repeat-entry convention: do not purchase the same stock twice
- FX convention: intentionally ignore FX conversion

This is a derived research strategy. It appears in the dashboard without
adding synthetic trades to the append-only manual ledger.

## Inception-to-Date Result

| Metric | Result |
|---|---:|
| Purchased stocks | `123` |
| Active positions | `123` |
| Deployed capital | `$123,000.00` |
| Ending value | `$174,475.30` |
| Gain / loss | `$51,475.30` |
| Return on deployed capital | `+41.85%` |

## First-Entry Signal Category Results

| Rank | First Signal | Entries | Deployed Capital | Gain / Loss | Return |
|---:|---|---:|---:|---:|---:|
| 1 | `fresh` | `21` | `$21,000.00` | `$17,188.36` | `+81.85%` |
| 2 | `strict` | `8` | `$8,000.00` | `$4,803.00` | `+60.04%` |
| 3 | `near` | `94` | `$94,000.00` | `$29,483.94` | `+31.37%` |

## Comparison With Sell-on-None

| Strategy | Entry Cycles | Active Positions | Gain / Loss | Return |
|---|---:|---:|---:|---:|
| `watchlist-variable-buy-only` | `123` | `123` | `$51,475.30` | `+41.85%` |
| `watchlist-variable` | `333` | `21` | `$4,635.42` | `+1.39%` |

## Interpretation

The lower sell-on-`none` return was primarily caused by exits and repeated
re-entry churn. Stocks that briefly lost their signal were sold before some
of the larger subsequent gains. The buy-only strategy retained those winners.

This does not establish that buy-only is generally superior. The tracked
universe was selected over time and contains substantial hindsight bias.
Results exclude transaction costs, bid-ask spread, slippage, tax, and FX.
