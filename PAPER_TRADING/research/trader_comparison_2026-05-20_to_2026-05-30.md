# Trader Comparison: May 20, 2026 to May 30, 2026

Research snapshot generated: 2026-05-30

## Method

- Rebased every trader's ledger allocation at the May 20, 2026 market close.
- Valued each holding at the latest available close as of May 30, 2026.
- The latest available U.S. equity close was May 29, 2026 because May 30 was a
  Saturday.
- Preserved each trader's allocation sizes from `data/trades.csv`.
- Used fractional shares and USD values. Canadian listings were converted
  using the corresponding daily CAD/USD rates.
- This is a hypothetical same-window comparison. It does not overwrite the
  original January 1 simulations or the recorded May 20
  `long-term-watchlist` fills.

Run the comparison again with:

```powershell
python .\compare_investors.py --from-date 2026-05-20
```

## Ranking

| Rank | Trader | Initial Value | Current Value | Gain / Loss | Return |
|---:|---|---:|---:|---:|---:|
| 1 | `short-term-watchlist` | `$13,000.00` | `$19,584.54` | `$6,584.54` | `+50.65%` |
| 2 | `memory` | `$4,000.00` | `$4,914.14` | `$914.14` | `+22.85%` |
| 3 | `long-term-watchlist` | `$29,000.00` | `$35,402.76` | `$6,402.76` | `+22.08%` |
| 4 | `daily-watchlist-2026-06-01` | `$10,000.00` | `$11,761.89` | `$1,761.89` | `+17.62%` |
| 5 | `advanced-packaging` | `$6,000.00` | `$6,684.23` | `$684.23` | `+11.40%` |
| 6 | `chip_design` | `$8,000.00` | `$8,890.90` | `$890.90` | `+11.14%` |
| 7 | `silicon-wafers` | `$6,000.00` | `$6,663.13` | `$663.13` | `+11.05%` |
| 8 | `insta_watchlist` | `$13,000.00` | `$13,972.70` | `$972.70` | `+7.48%` |
| 9 | `bdinvesting` | `$46,000.00` | `$49,432.72` | `$3,432.72` | `+7.46%` |
| 10 | `deposition-etch` | `$5,000.00` | `$5,321.14` | `$321.14` | `+6.42%` |
| 11 | `leading-edge-logic-foundry` | `$3,000.00` | `$3,131.93` | `$131.93` | `+4.40%` |
| 12 | `cmp-cleaning-metrology` | `$5,000.00` | `$5,201.54` | `$201.54` | `+4.03%` |
| 13 | `raw-materials-specialty-gases` | `$7,000.00` | `$7,248.98` | `$248.98` | `+3.56%` |
| 14 | `russellckai` | `$10,000.00` | `$10,347.97` | `$347.97` | `+3.48%` |
| 15 | `photomasks-eda` | `$7,000.00` | `$7,240.63` | `$240.63` | `+3.44%` |
| 16 | `nisarg` | `$72,471.31` | `$74,555.87` | `$2,084.55` | `+2.88%` |
| 17 | `brandon` | `$10,000.00` | `$10,229.67` | `$229.67` | `+2.30%` |
| 18 | `lithography` | `$3,000.00` | `$3,051.45` | `$51.45` | `+1.71%` |
| 19 | `amswann` | `$35,000.00` | `$35,477.77` | `$477.77` | `+1.37%` |
| 20 | `joyeeyang` | `$33,000.00` | `$33,043.81` | `$43.81` | `+0.13%` |

## Notes

The `short-term-watchlist`, `memory`, and `long-term-watchlist` results are
strongly influenced by a short market window and volatile names. Treat the
ranking as a momentum snapshot, not evidence of a durable strategy.

The `nisarg` row is calculated from imported Wealthsimple activity history.
It excludes deposits, withdrawals, dividends, interest, fees, and FX cash
movements. It includes opening holdings, post-opening security purchases,
sale proceeds, corporate actions, corrections, staking rewards, and remaining
security positions. The physically backed `GOLD` position uses gold futures
(`GC=F`) as a transparent valuation proxy because the export does not include
an exchange ticker.
