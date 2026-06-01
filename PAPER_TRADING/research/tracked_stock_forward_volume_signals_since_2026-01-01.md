# Forward Volume Signal Study for Tracked Stocks

Research snapshot generated: 2026-06-01

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
| All observations | `13736` | `15.9%` | `22.6%` | `0.97x` | `1.32x` | `+2.90%` |
| 5d volume >= 1.5x normal | `1125` | `30.8%` | `37.4%` | `1.14x` | `1.60x` | `+3.42%` |
| 5d price return >= +10% | `1857` | `27.6%` | `32.4%` | `1.13x` | `1.54x` | `+6.33%` |
| 5d volume >= 1.5x and price >= +10% | `319` | `45.5%` | `47.3%` | `1.38x` | `1.87x` | `+4.46%` |
| Near 20d high and 5d volume >= 1.25x | `884` | `38.5%` | `43.8%` | `1.29x` | `1.82x` | `+3.15%` |
| 5d volume >= 1.5x, price >= +10%, near 20d high | `208` | `53.8%` | `56.7%` | `1.55x` | `2.24x` | `+5.42%` |
| 4+ rising-volume sessions and price >= +5% | `455` | `32.1%` | `36.3%` | `1.23x` | `1.74x` | `+4.46%` |

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
| `MOV` | 2026-06-01 | `+32.27%` | `2.09x` | `-1.70%` | yes |
| `RCAT` | 2026-06-01 | `+57.70%` | `1.92x` | `+2.34%` | yes |
| `HPQ` | 2026-06-01 | `+16.24%` | `1.91x` | `+8.51%` | yes |
| `SNOW` | 2026-06-01 | `+62.69%` | `1.83x` | `+9.63%` | yes |
| `IBM` | 2026-06-01 | `+26.23%` | `1.70x` | `+7.60%` | yes |
| `GRRR` | 2026-06-01 | `+44.99%` | `1.67x` | `+3.22%` | yes |
| `TEO` | 2026-06-01 | `+22.43%` | `1.66x` | `-1.29%` | yes |
| `BOX` | 2026-06-01 | `+11.16%` | `1.59x` | `+6.79%` | yes |
| `ONDS` | 2026-06-01 | `+48.57%` | `1.51x` | `+1.58%` | yes |
| `AXTA` | 2026-06-01 | `+4.00%` | `1.77x` | `-1.23%` | near |
| `BRZE` | 2026-06-01 | `+16.10%` | `1.50x` | `+10.30%` | near |
| `CRNC` | 2026-06-01 | `+16.03%` | `1.49x` | `-0.93%` | near |
| `BTDR` | 2026-06-01 | `+26.35%` | `1.49x` | `+0.71%` | near |
| `CLF` | 2026-06-01 | `+20.93%` | `1.48x` | `-0.15%` | near |
| `BBAR` | 2026-06-01 | `+23.10%` | `1.48x` | `+2.51%` | near |
| `MRVL` | 2026-06-01 | `+11.77%` | `1.46x` | `+5.36%` | near |
| `BHVN` | 2026-06-01 | `+20.95%` | `1.46x` | `+1.24%` | near |
| `PATH` | 2026-06-01 | `+19.85%` | `1.41x` | `+11.77%` | near |
| `KXIAY` | 2026-06-01 | `+33.10%` | `1.33x` | `+12.72%` | near |
| `SOFI` | 2026-06-01 | `+18.95%` | `1.28x` | `+1.98%` | near |
| `SERV` | 2026-06-01 | `+8.28%` | `1.27x` | `-1.67%` | near |

## Data

The sortable rolling observations are in
`research/tracked_stock_forward_volume_signals_since_2026-01-01.csv`.

Source: [Yahoo Finance](https://finance.yahoo.com/) public chart feed.
