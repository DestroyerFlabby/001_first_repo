# Forward Volume Signal Study for Tracked Stocks

Research snapshot generated: 2026-05-30

## Question

Which observable technical conditions were associated with elevated trading
volume during the next five sessions?

## Method

- Screened `140` unique tracked stock tickers from `data/trades.csv`.
- Used rolling daily observations from January 2, 2026 onward.
- Used only information available by each observation date.
- Defined normal volume as the prior 20-session average.
- Defined future average-volume expansion as next-five-session average volume
  at least `1.5x` normal.
- Defined future peak-volume expansion as at least one of the next five sessions
  reaching `2.0x` normal volume.
- This is descriptive analysis on a selected tracked universe, not an
  out-of-sample trading model.

## Results

| Pre-Existing Condition | Observations | Next 5d Avg Volume >=1.5x | Next 5d Peak Volume >=2x | Median Next Avg Volume | Median Next Peak Volume | Median Next 5d Max Return |
|---|---:|---:|---:|---:|---:|---:|
| All observations | `13598` | `15.8%` | `22.4%` | `0.97x` | `1.32x` | `+2.89%` |
| 5d volume >= 1.5x normal | `1122` | `30.8%` | `37.4%` | `1.14x` | `1.60x` | `+3.42%` |
| 5d price return >= +10% | `1831` | `27.3%` | `32.2%` | `1.13x` | `1.54x` | `+6.23%` |
| 5d volume >= 1.5x and price >= +10% | `318` | `45.3%` | `47.2%` | `1.38x` | `1.87x` | `+4.44%` |
| Near 20d high and 5d volume >= 1.25x | `878` | `38.3%` | `43.6%` | `1.29x` | `1.82x` | `+3.12%` |
| 5d volume >= 1.5x, price >= +10%, near 20d high | `207` | `53.6%` | `56.5%` | `1.55x` | `2.22x` | `+5.41%` |
| 4+ rising-volume sessions and price >= +5% | `448` | `31.9%` | `36.2%` | `1.23x` | `1.74x` | `+4.37%` |

## Interpretation

The practical watch condition is a combination: price strength near a
recent high plus already-expanding volume. Rising volume without price
strength is noisier, and price strength without volume offers less
evidence that attention is broadening.

For live screening, prioritize names where:

1. Five-session return is at least `+10%`.
2. Five-session average volume is at least `1.5x` the prior 20-session average.
3. The close is within `2%` of its prior 20-session high.
4. A company-specific catalyst can be identified separately.

This flags names where additional volume is more plausible. It does not
establish that the next price move will be positive.

## Latest Live Screen

The rows below use the latest available close and therefore do not have
known next-five-session outcomes yet.

| Ticker | As Of | Prior 5d Return | Prior 5d Volume Ratio | Distance to Prior 20d High | Strict Match |
|---|---|---:|---:|---:|---|
| `CRSR` | 2026-05-29 | `+75.18%` | `2.64x` | `+1.59%` | yes |
| `UMAC` | 2026-05-29 | `+114.73%` | `2.22x` | `+7.36%` | yes |
| `QBTS` | 2026-05-29 | `+17.09%` | `1.99x` | `+2.20%` | yes |
| `MOV` | 2026-05-29 | `+39.20%` | `1.96x` | `+7.56%` | yes |
| `IBM` | 2026-05-29 | `+17.72%` | `1.87x` | `+12.71%` | yes |
| `RCAT` | 2026-05-29 | `+60.58%` | `1.70x` | `+2.47%` | yes |
| `HPQ` | 2026-05-29 | `+23.47%` | `1.68x` | `+6.08%` | yes |
| `SNOW` | 2026-05-29 | `+54.37%` | `1.62x` | `+6.84%` | yes |
| `BBAR` | 2026-05-29 | `+12.85%` | `1.55x` | `+4.14%` | yes |
| `AXTA` | 2026-05-29 | `+5.63%` | `1.62x` | `+1.45%` | near |
| `TEO` | 2026-05-29 | `+23.93%` | `1.50x` | `+5.22%` | near |
| `GRRR` | 2026-05-29 | `+43.62%` | `1.48x` | `+15.45%` | near |
| `BRZE` | 2026-05-29 | `+9.48%` | `1.48x` | `+0.71%` | near |
| `BOX` | 2026-05-29 | `+6.14%` | `1.42x` | `+4.09%` | near |
| `CLF` | 2026-05-29 | `+27.10%` | `1.42x` | `+2.33%` | near |
| `MRVL` | 2026-05-29 | `+7.50%` | `1.41x` | `-1.57%` | near |
| `ONDS` | 2026-05-29 | `+44.01%` | `1.39x` | `-0.23%` | near |
| `BIRK` | 2026-05-29 | `+13.61%` | `1.37x` | `+2.27%` | near |
| `CRNC` | 2026-05-29 | `+32.71%` | `1.36x` | `+8.34%` | near |
| `PATH` | 2026-05-29 | `+10.88%` | `1.35x` | `+1.21%` | near |

## Data

The sortable rolling observations are in
`research/tracked_stock_forward_volume_signals_since_2026-01-01.csv`.

Source: [Yahoo Finance](https://finance.yahoo.com/) public chart feed.
