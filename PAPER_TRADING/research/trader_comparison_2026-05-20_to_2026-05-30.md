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
  original January 1 simulations or the recorded May 20 `WATCHLIST` fills.

Run the comparison again with:

```powershell
python .\compare_investors.py --from-date 2026-05-20
```

## Ranking

| Rank | Trader | Initial Value | Current Value | Gain / Loss | Return |
|---:|---|---:|---:|---:|---:|
| 1 | `WATCHLIST` | `$29,000.00` | `$35,402.76` | `$6,402.76` | `+22.08%` |
| 2 | `bdinvesting` | `$46,000.00` | `$49,420.09` | `$3,420.09` | `+7.43%` |
| 3 | `russellckai` | `$10,000.00` | `$10,347.97` | `$347.97` | `+3.48%` |
| 4 | `Nisarg` | `$72,471.31` | `$74,555.87` | `$2,084.55` | `+2.88%` |
| 5 | `Brandon` | `$10,000.00` | `$10,223.54` | `$223.54` | `+2.24%` |
| 6 | `amswann` | `$35,000.00` | `$35,471.63` | `$471.63` | `+1.35%` |
| 7 | `joyeeyang` | `$33,000.00` | `$33,031.30` | `$31.30` | `+0.09%` |

## Notes

The `WATCHLIST` result is strongly influenced by volatile names. Its largest
contributors during the window were `MNTS`, `RDW`, and `QBTS`. A short-window
ranking should be treated as a momentum snapshot, not evidence of a durable
strategy.

The `Nisarg` row is calculated from imported Wealthsimple activity history.
It excludes deposits, withdrawals, dividends, interest, fees, and FX cash
movements. It includes opening holdings, post-opening security purchases,
sale proceeds, corporate actions, corrections, staking rewards, and remaining
security positions. The physically backed `GOLD` position uses gold futures
(`GC=F`) as a transparent valuation proxy because the export does not include
an exchange ticker.
