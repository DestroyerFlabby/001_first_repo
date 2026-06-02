# Watchlist Variable Strategy: January 31, 2026 to June 1, 2026

Research snapshot generated: 2026-06-01

## Strategy Convention

- Dashboard trader name: `watchlist-variable`
- Strategy inception: `2026-01-31`
- Universe: the currently tracked `stock` symbols in `data/trades.csv`,
  evaluated historically from strategy inception
- Signal source: the five-session signal classification calculated using
  information available at each EOD close
- Eligible signals: `fresh`, `strict`, and `near`
- Excluded signal: `none`
- Execution convention: observe the EOD signal and trade at the next available
  market close to avoid using future information
- Entry amount: `$1,000` per stock per entry cycle
- Exit convention: sell the full position after its signal changes to `none`
- FX convention: intentionally ignore FX conversion

This is a derived research strategy. It appears in the dashboard without
adding hundreds of synthetic rows to the append-only manual trade ledger.

## Inception-to-Date Result

| Metric | Result |
|---|---:|
| Entry cycles | `333` |
| Closed cycles | `312` |
| Active positions | `21` |
| Cumulative deployed capital | `$333,000.00` |
| Ending value | `$337,635.42` |
| Gain / loss | `$4,635.42` |
| Return on cumulative deployed capital | `+1.39%` |

## Entry Signal Category Results

| Rank | Entry Signal | Entries | Closed | Open | Deployed Capital | Gain / Loss | Return |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `strict` | `34` | `28` | `6` | `$34,000.00` | `$2,060.82` | `+6.06%` |
| 2 | `fresh` | `47` | `44` | `3` | `$47,000.00` | `$941.13` | `+2.00%` |
| 3 | `near` | `252` | `240` | `12` | `$252,000.00` | `$1,633.47` | `+0.65%` |

## Interpretation

`strict` entries performed best in this tracked-universe simulation. `near`
signals produced positive results but required substantially more entry cycles
for a lower return on deployed capital. This is a short historical sample and
does not include transaction costs, bid-ask spread, slippage, tax, or FX.
