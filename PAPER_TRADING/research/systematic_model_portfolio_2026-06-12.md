# Systematic Model Portfolio

Created: 2026-06-12

## Objective

Build a diversified model portfolio from stocks already registered in the paper-trading system, starting on 2026-01-31 and making every decision using only information available through the prior market close.

## Point-in-Time Rules

- A stock cannot enter before `asset_universe.added_at`.
- Only rows with `strategy_eligible=true` are considered.
- Price, volume, technical signals, relative strength, and historical news counts are truncated at the observation date.
- Signals observed after one close generate dollar orders for the next available close.
- January 31, 2026 was a Saturday, so the first executable session uses information available through Friday, January 30 and trades on Monday, February 2.

## Construction

- Initial capital: $100,000.
- Target invested capital: 95%; unused capital remains cash.
- Maximum holdings: 25.
- Maximum single-name target: 7%.
- Maximum sector target: 25%.
- Maximum names per sector: 5.
- Rebalance only when target drift exceeds 3% of portfolio value, unless entering or exiting.
- A holding must remain outside the qualified set for 10 sessions before full exit.

## Ranking Inputs

- Existing multi-horizon signal score.
- Fresh, strict, and near classifications.
- Relative strength versus SPY.
- Volume confirmation.
- Distance from recent highs and overextension controls.
- One-month and three-month confirmation.
- Seven-day news activity and acceleration.
- Annualized trailing volatility penalty.

Near signals require a higher score than fresh or strict signals.

## Portfolio Statistics

The dedicated dashboard tab reports:

- Return, gain/loss, cash, and current value.
- Alpha versus SPY, volatility, and maximum drawdown.
- Current holdings and weights.
- Current sector exposure and concentration.
- Closed-position win rate and median return.
- Total turnover and trade count.
- Daily rebalance history.
- Full simulated trade ledger.
- Pending next-close orders based on the latest selected date.

## Research Basis

The implementation follows the practical principles supported by factor and portfolio-construction research: momentum and relative strength can be useful ranking inputs, but construction, diversification, risk caps, and rebalance discipline materially affect realized results. Rebalance bands are used to avoid reacting to immaterial daily weight changes.

## Limitations

- `asset_universe.added_at` is used as the historical availability date. Incorrect dates can create survivorship or data-entry bias.
- Historical news coverage ends at the latest committed news-count date and is only a bounded score input.
- No commissions, taxes, bid/ask spread, FX costs, or market impact are modeled.
- This is a research simulation, not investment advice or a broker-connected portfolio.
