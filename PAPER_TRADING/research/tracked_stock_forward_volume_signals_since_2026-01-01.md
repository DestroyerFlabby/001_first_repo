# Forward Volume Signal Study for Tracked Stocks

Research snapshot generated: 2026-05-30

## Question

Which observable technical conditions were associated with elevated trading
volume during the next five sessions?

## Method

- Screened `87` unique tracked stock tickers from `data/trades.csv`.
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
| All observations | `8457` | `15.7%` | `21.4%` | `0.97x` | `1.32x` | `+2.57%` |
| 5d volume >= 1.5x normal | `696` | `29.5%` | `34.6%` | `1.14x` | `1.58x` | `+3.09%` |
| 5d price return >= +10% | `1107` | `25.7%` | `30.8%` | `1.12x` | `1.51x` | `+6.67%` |
| 5d volume >= 1.5x and price >= +10% | `202` | `38.1%` | `41.1%` | `1.25x` | `1.67x` | `+3.99%` |
| Near 20d high and 5d volume >= 1.25x | `506` | `37.7%` | `43.3%` | `1.32x` | `1.84x` | `+2.69%` |
| 5d volume >= 1.5x, price >= +10%, near 20d high | `121` | `47.9%` | `52.1%` | `1.47x` | `2.05x` | `+4.41%` |
| 4+ rising-volume sessions and price >= +5% | `264` | `30.7%` | `31.4%` | `1.22x` | `1.69x` | `+4.59%` |

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
| `QBTS` | 2026-05-29 | `+17.09%` | `1.99x` | `+2.20%` | yes |
| `IBM` | 2026-05-29 | `+17.72%` | `1.87x` | `+12.71%` | yes |
| `SNOW` | 2026-05-29 | `+54.37%` | `1.62x` | `+6.84%` | yes |

## Data

The sortable rolling observations are in
`research/tracked_stock_forward_volume_signals_since_2026-01-01.csv`.

Source: [Yahoo Finance](https://finance.yahoo.com/) public chart feed.
