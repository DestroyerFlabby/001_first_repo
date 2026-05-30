# Tracked Stock Volume Spikes Since January 1, 2026

Research snapshot generated: 2026-05-30

## Scope

- Screened `140` unique tracked `stock` tickers from `data/trades.csv`.
- Excluded ETFs and crypto.
- Used the January 2, 2026 close because January 1 was a market holiday.
- Defined a spike as the first close at least `25%` above the January 2 close.
- Compared average volume during the five sessions immediately before the
  threshold date with the preceding 20-session average volume.
- Used Yahoo Finance's public chart feed for split-adjusted chart history.
- This is a tracked-ledger screen, not a scan of every listed public company.

## Summary

- Stocks crossing the `+25%` threshold: `78`.
- Crossings with enough pre-spike sessions for a volume comparison: `70`.
- Five-day pre-spike volume at least `1.5x` prior volume: `14 / 70`.
- Threshold-day volume at least `1.5x` prior volume: `35 / 70`.
- Median five-day pre-spike volume ratio: `1.05x`.
- Median threshold-day volume ratio: `1.48x`.
- Positive price momentum during the five sessions before crossing: `70 / 70`.
- Median five-session price return immediately before crossing: `14.41%`.

## Pattern Read

The strongest recurring early signal in this tracked sample was price
momentum, not volume alone: every measurable name was already rising during
the five sessions before its first `+25%` close. Volume more often acted as
confirmation on the threshold day than as a reliable early-warning signal.

The useful distinction is whether volume expanded before the threshold
crossing or only on the crossing day. A pre-spike ratio above `1.5x` can
flag accumulation or an information-driven repricing already underway.
A threshold-day-only surge is more consistent with a discrete catalyst.
No volume expansion does not invalidate a move: sustained trends can cross
the threshold after their heaviest trading has already occurred.

Treat this as a screening signal, not a trading rule. Small-cap names can
show extreme ratios because their prior liquidity was thin. News review,
float, dilution, short interest, and valuation still need separate checks.

## Results

| Ticker | First +25% Date | Return at Crossing | Latest Return | Pre-Spike Volume Ratio | Threshold-Day Ratio | Pattern |
|---|---|---:|---:|---:|---:|---|
| `SNDK` | 2026-01-06 | `27.03%` | `+515.82%` | `x` | `x` | insufficient pre-spike sessions |
| `AXTI` | 2026-01-07 | `43.85%` | `+515.51%` | `x` | `x` | insufficient pre-spike sessions |
| `KXIAY` | 2026-01-13 | `26.34%` | `+499.05%` | `1.72x` | `1.35x` | volume expanded before threshold |
| `SATL` | 2026-01-08 | `48.98%` | `+385.20%` | `x` | `x` | insufficient pre-spike sessions |
| `AAOI` | 2026-02-20 | `30.51%` | `+300.03%` | `0.56x` | `1.45x` | no >=1.5x volume expansion |
| `WOLF` | 2026-04-09 | `29.05%` | `+213.15%` | `0.77x` | `2.95x` | volume expanded on threshold day |
| `ARM` | 2026-03-25 | `36.90%` | `+207.93%` | `2.03x` | `7.70x` | volume expanded before threshold |
| `MU` | 2026-01-22 | `26.05%` | `+207.84%` | `1.17x` | `1.16x` | no >=1.5x volume expansion |
| `MNTS` | 2026-01-05 | `53.66%` | `+193.55%` | `x` | `x` | insufficient pre-spike sessions |
| `SPIR` | 2026-01-08 | `33.29%` | `+192.45%` | `x` | `x` | insufficient pre-spike sessions |
| `INTC` | 2026-01-21 | `37.76%` | `+191.21%` | `1.27x` | `1.93x` | volume expanded on threshold day |
| `RDW` | 2026-01-16 | `29.68%` | `+172.09%` | `1.10x` | `1.88x` | volume expanded on threshold day |
| `SUOPY` | 2026-02-27 | `25.54%` | `+165.52%` | `1.01x` | `0.18x` | no >=1.5x volume expansion |
| `MRAM` | 2026-01-16 | `31.61%` | `+162.23%` | `0.75x` | `1.28x` | no >=1.5x volume expansion |
| `NBIS` | 2026-03-13 | `25.57%` | `+156.91%` | `1.06x` | `1.11x` | no >=1.5x volume expansion |
| `SMSN.IL` | 2026-01-28 | `26.24%` | `+140.53%` | `0.73x` | `1.31x` | no >=1.5x volume expansion |
| `UMAC` | 2026-01-15 | `28.67%` | `+134.19%` | `1.33x` | `1.52x` | volume expanded on threshold day |
| `AMD` | 2026-04-21 | `27.31%` | `+130.95%` | `1.09x` | `1.15x` | no >=1.5x volume expansion |
| `MRVL` | 2026-04-08 | `28.03%` | `+129.33%` | `1.35x` | `1.24x` | no >=1.5x volume expansion |
| `ASX` | 2026-02-09 | `31.38%` | `+127.46%` | `1.60x` | `1.69x` | volume expanded before threshold |
| `SSLLF` | 2026-04-10 | `32.50%` | `+121.99%` | `0.00x` | `3.33x` | volume expanded on threshold day |
| `LITE` | 2026-02-05 | `30.64%` | `+121.43%` | `1.68x` | `1.96x` | volume expanded before threshold |
| `GFS` | 2026-01-27 | `28.59%` | `+116.90%` | `1.45x` | `1.68x` | volume expanded on threshold day |
| `ON` | 2026-02-11 | `25.54%` | `+112.73%` | `1.54x` | `1.33x` | volume expanded before threshold |
| `CRSR` | 2026-05-08 | `30.90%` | `+101.66%` | `1.47x` | `4.88x` | volume expanded on threshold day |
| `OUST` | 2026-05-06 | `25.78%` | `+97.05%` | `1.71x` | `3.16x` | volume expanded before threshold |
| `RKLB` | 2026-01-16 | `26.73%` | `+88.81%` | `0.72x` | `1.08x` | no >=1.5x volume expansion |
| `COHR` | 2026-02-20 | `27.71%` | `+86.01%` | `0.77x` | `1.07x` | no >=1.5x volume expansion |
| `Q` | 2026-02-10 | `28.62%` | `+83.57%` | `0.90x` | `1.76x` | volume expanded on threshold day |
| `MOV` | 2026-04-09 | `26.80%` | `+82.20%` | `0.84x` | `1.17x` | no >=1.5x volume expansion |
| `VRT` | 2026-02-11 | `41.51%` | `+79.78%` | `1.48x` | `4.08x` | volume expanded on threshold day |
| `ACLS` | 2026-04-09 | `25.69%` | `+74.65%` | `0.73x` | `0.88x` | no >=1.5x volume expansion |
| `LRCX` | 2026-01-27 | `28.86%` | `+71.93%` | `0.76x` | `0.80x` | no >=1.5x volume expansion |
| `POET` | 2026-04-21 | `43.16%` | `+71.65%` | `1.96x` | `5.85x` | volume expanded before threshold |
| `AMAT` | 2026-01-28 | `25.25%` | `+67.39%` | `0.80x` | `1.03x` | no >=1.5x volume expansion |
| `LYSCF` | 2026-01-14 | `27.39%` | `+64.35%` | `0.57x` | `1.01x` | no >=1.5x volume expansion |
| `GRRR` | 2026-05-26 | `30.74%` | `+62.67%` | `0.77x` | `2.61x` | volume expanded on threshold day |
| `AMKR` | 2026-02-11 | `30.87%` | `+62.07%` | `1.48x` | `1.34x` | no >=1.5x volume expansion |
| `ASMIY` | 2026-01-20 | `26.27%` | `+59.79%` | `1.05x` | `9.13x` | volume expanded on threshold day |
| `CLSK` | 2026-05-06 | `25.54%` | `+58.35%` | `0.97x` | `1.35x` | no >=1.5x volume expansion |
| `RCAT` | 2026-01-08 | `29.15%` | `+58.30%` | `x` | `x` | insufficient pre-spike sessions |
| `PANW` | 2026-05-13 | `26.99%` | `+57.04%` | `1.26x` | `1.29x` | no >=1.5x volume expansion |
| `ONTO` | 2026-01-15 | `31.34%` | `+55.69%` | `0.92x` | `1.88x` | volume expanded on threshold day |
| `ENTG` | 2026-01-15 | `26.78%` | `+54.97%` | `0.71x` | `1.91x` | volume expanded on threshold day |
| `SHECY` | 2026-02-27 | `25.26%` | `+54.15%` | `0.87x` | `0.47x` | no >=1.5x volume expansion |
| `BTDR` | 2026-01-14 | `27.79%` | `+51.43%` | `0.81x` | `2.73x` | volume expanded on threshold day |
| `HLIT` | 2026-05-08 | `27.84%` | `+50.80%` | `1.50x` | `2.40x` | volume expanded on threshold day |
| `KLAC` | 2026-01-27 | `26.82%` | `+50.79%` | `1.18x` | `1.06x` | no >=1.5x volume expansion |
| `IREN` | 2026-01-16 | `35.41%` | `+48.81%` | `1.23x` | `1.56x` | volume expanded on threshold day |
| `TOELY` | 2026-02-18 | `25.38%` | `+48.73%` | `0.71x` | `0.89x` | no >=1.5x volume expansion |
| `CIFR` | 2026-05-05 | `36.42%` | `+45.99%` | `0.73x` | `2.46x` | volume expanded on threshold day |
| `QCOM` | 2026-05-08 | `26.66%` | `+45.12%` | `1.93x` | `2.28x` | volume expanded before threshold |
| `LPTH` | 2026-04-16 | `27.30%` | `+44.88%` | `1.44x` | `1.75x` | volume expanded on threshold day |
| `ASML` | 2026-01-29 | `25.04%` | `+38.58%` | `1.27x` | `1.29x` | no >=1.5x volume expansion |
| `SHLS` | 2026-05-27 | `33.33%` | `+36.96%` | `0.81x` | `1.65x` | volume expanded on threshold day |
| `ASTS` | 2026-01-16 | `38.70%` | `+35.87%` | `0.81x` | `1.73x` | volume expanded on threshold day |
| `UMICY` | 2026-05-13 | `39.89%` | `+34.75%` | `0.86x` | `1.29x` | no >=1.5x volume expansion |
| `TSM` | 2026-04-24 | `25.92%` | `+30.93%` | `1.00x` | `1.58x` | volume expanded on threshold day |
| `SOBO` | 2026-05-04 | `25.22%` | `+29.64%` | `1.04x` | `0.90x` | no >=1.5x volume expansion |
| `AVGO` | 2026-05-14 | `26.51%` | `+28.52%` | `0.94x` | `0.95x` | no >=1.5x volume expansion |
| `TEO` | 2026-05-29 | `27.47%` | `+27.47%` | `1.95x` | `3.25x` | volume expanded before threshold |
| `ONDS` | 2026-01-08 | `27.13%` | `+19.96%` | `x` | `x` | insufficient pre-spike sessions |
| `TRP` | 2026-05-20 | `25.40%` | `+19.53%` | `0.36x` | `0.55x` | no >=1.5x volume expansion |
| `GOOG` | 2026-05-06 | `25.31%` | `+19.38%` | `1.55x` | `1.39x` | volume expanded before threshold |
| `ANET` | 2026-04-21 | `29.39%` | `+19.36%` | `1.01x` | `1.31x` | no >=1.5x volume expansion |
| `MP` | 2026-01-14 | `26.07%` | `+17.70%` | `1.37x` | `1.59x` | volume expanded on threshold day |
| `CCO` | 2026-01-21 | `25.02%` | `+14.44%` | `0.70x` | `1.20x` | no >=1.5x volume expansion |
| `SIDU` | 2026-04-16 | `37.41%` | `+13.39%` | `1.93x` | `2.22x` | volume expanded before threshold |
| `COST` | 2026-05-18 | `25.98%` | `+11.92%` | `1.05x` | `1.28x` | no >=1.5x volume expansion |
| `FNV` | 2026-01-28 | `26.99%` | `+11.63%` | `1.41x` | `1.16x` | no >=1.5x volume expansion |
| `NINOY` | 2026-05-14 | `31.72%` | `+6.92%` | `4.96x` | `3.06x` | volume expanded before threshold |
| `LMT` | 2026-01-29 | `25.24%` | `+6.72%` | `0.59x` | `1.60x` | volume expanded on threshold day |
| `GME` | 2026-02-02 | `25.36%` | `+2.72%` | `2.68x` | `3.78x` | volume expanded before threshold |
| `BHVN` | 2026-01-22 | `26.94%` | `+1.57%` | `0.85x` | `0.70x` | no >=1.5x volume expansion |
| `FLNC` | 2026-01-28 | `34.68%` | `-17.95%` | `0.92x` | `1.15x` | no >=1.5x volume expansion |
| `SERV` | 2026-01-08 | `30.26%` | `-20.96%` | `x` | `x` | insufficient pre-spike sessions |
| `CUPR` | 2026-04-07 | `49.75%` | `-25.37%` | `15.30x` | `68.97x` | volume expanded before threshold |
| `EOSE` | 2026-01-13 | `29.68%` | `-35.00%` | `1.41x` | `2.16x` | volume expanded on threshold day |

## Data

The sortable per-stock measurements are in
`research/tracked_stock_volume_spikes_since_2026-01-01.csv`.

Source: [Yahoo Finance](https://finance.yahoo.com/) public chart feed.
