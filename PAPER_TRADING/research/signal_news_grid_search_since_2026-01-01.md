# Signal And News Grid Search Since 2026-01-01

## Scope

- Simulated window: `2026-01-01` to `2026-06-01`.
- Committed Alpaca daily news counts currently end on `2026-06-01`.
- Tested combinations: `432`.
- Signals and news use information visible by the prior close. Trades execute at the next available close.
- The top rows are optimized on this same historical sample. They are hypotheses for forward tracking, not validated predictions.

## Top 20 By Return

- Train/test reference split: `2026-01-01` to `2026-03-31` and `2026-04-01` to `2026-06-01`.

| Rank | Entry signal | Entry news | Exit news | Missing-signal sessions | 1m cutoff | Entries | Gain | Full return | Train return | Test return |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | fresh-only | accelerating | zero | 20 | -5% | 60 | $26,833.14 | 44.72% | 3.21% | 29.82% |
| 2 | fresh-only | accelerating | zero | 20 | -10% | 60 | $26,647.37 | 44.41% | 2.70% | 29.82% |
| 3 | fresh-only | accelerating | zero | 15 | -5% | 62 | $26,103.98 | 42.10% | 1.44% | 29.82% |
| 4 | fresh-or-strict | accelerating | zero | 20 | -10% | 83 | $34,762.45 | 41.88% | 0.45% | 29.18% |
| 5 | fresh-only | accelerating | zero | 15 | -10% | 62 | $25,955.19 | 41.86% | 1.04% | 29.82% |
| 6 | fresh-only | accelerating | zero | 10 | -5% | 62 | $25,890.71 | 41.76% | 0.93% | 29.82% |
| 7 | fresh-only | accelerating | zero | 10 | -10% | 62 | $25,713.29 | 41.47% | 0.46% | 29.82% |
| 8 | fresh-or-strict | accelerating | zero | 20 | -5% | 84 | $34,837.26 | 41.47% | 0.87% | 28.19% |
| 9 | fresh-only | active | zero | 20 | -5% | 70 | $28,830.18 | 41.19% | -0.13% | 30.35% |
| 10 | fresh-only | active | zero | 20 | -10% | 70 | $28,783.55 | 41.12% | -0.52% | 30.35% |
| 11 | fresh-only | accelerating | zero | 5 | -5% | 62 | $25,097.30 | 40.48% | 0.71% | 29.82% |
| 12 | fresh-only | accelerating | zero | 5 | -10% | 62 | $24,925.64 | 40.20% | 0.25% | 29.82% |
| 13 | fresh-or-strict | active | zero | 20 | -10% | 89 | $35,696.50 | 40.11% | -1.70% | 29.44% |
| 14 | fresh-or-strict | active | zero | 20 | -5% | 90 | $35,632.16 | 39.59% | -1.37% | 28.51% |
| 15 | fresh-only | active | zero | 15 | -10% | 73 | $28,051.20 | 38.43% | -1.66% | 30.35% |
| 16 | fresh-only | active | zero | 15 | -5% | 73 | $27,981.61 | 38.33% | -1.36% | 30.35% |
| 17 | fresh-only | active | zero | 10 | -5% | 73 | $27,674.32 | 37.91% | -1.89% | 30.35% |
| 18 | fresh-or-strict | accelerating | zero | 15 | -10% | 86 | $32,593.46 | 37.90% | -0.96% | 28.67% |
| 19 | fresh-only | active | zero | 10 | -10% | 73 | $27,593.50 | 37.80% | -2.24% | 30.35% |
| 20 | fresh-or-strict | accelerating | zero | 15 | -5% | 87 | $32,697.23 | 37.58% | -0.50% | 27.70% |

## Interpretation

Use this ranking to select a small number of forward-tracking candidates. Do not promote the highest-return row directly into a live rule: testing hundreds of combinations creates overfitting risk.

The full sortable result set is in `research\signal_news_grid_search_since_2026-01-01.csv`.
