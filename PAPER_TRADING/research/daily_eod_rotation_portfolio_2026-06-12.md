# Daily EOD Rotation Portfolio

## Purpose

This portfolio is the high-turnover comparison strategy for the systematic model portfolio. It starts on 2026-01-31, uses the same point-in-time tracked-stock universe, and uses only information available through each observation date.

It is an EOD rotation strategy, not an intraday backtest. A signal observed at one market close generates an order for the next available close.

## Rules

- Initial capital: $100,000
- Maximum positions: 10
- Target invested capital: 95%
- Maximum position weight: 12%
- Maximum sector weight: 30%
- Maximum names per sector: 3
- Rebalance threshold: 1.5% of portfolio value
- Signals: fresh and strict normally qualify; near requires a higher rotation score
- Ranking: short momentum, relative strength, volume expansion, news acceleration, overextension control, and volatility control
- Universe timing: a stock cannot enter before its `asset_universe.added_at` date
- Execution timing: next available close after the signal observation date

## Initial Replay Through 2026-06-12

- Portfolio return: -3.23%
- Ending value: $96,769.31
- Total trades: 258
- Completed rotations: 115
- Closed-position win rate: 47.83%
- Median closed-position return: -0.26%
- Cumulative traded value / initial capital: 2,664.69%

The initial result shows that the faster strategy was worse than the slower systematic model over this window. The high turnover and slightly negative median closed trade are material weaknesses. The strategy remains useful as a transparent comparison and as evidence against assuming that more frequent signal reactions improve results.

## Limitations

- No commissions, bid/ask spread, slippage, taxes, or market impact are modeled.
- Daily bars cannot represent intraday entry timing or execution quality.
- Historical universe quality depends on the accuracy of `added_at` and `archived_at` dates.
- Results should not be tuned against this same window without a later holdout period.
