# Mass-Change Watchlist Strategy

The `watchlist-variable-mass-change` portfolio is a sector-led discovery-stage
strategy. It is designed to identify trending sectors first, then collect
candidate stocks inside those sectors before they are mature enough for the
short-term or long-term watchlists.

## Source of Truth

Candidate membership lives in:

`data/mass_change_watchlist.csv`

Fields:

- `ticker`
- `security_type`
- `added_date`
- `sector`
- `theme`
- `source`
- `reason`
- `confidence`
- `notes`

This file is not a trade ledger. It is an auditable sector-and-candidate list
used by the dashboard strategy.

## Sector-First Process

The discovery flow should run in this order:

1. Detect active sectors or themes from market movers, social attention, news,
   and creator observations.
2. Score the sector for breadth, news acceleration, social acceleration, and
   volume expansion.
3. Identify stocks inside the sector that are participating or beginning to
   participate.
4. Add verified names only to `data/mass_change_watchlist.csv`.
5. Let dashboard signal logic determine whether simulated entries occur.

## Discovery Inputs

Use multiple source families before assigning high confidence:

- Unusual sector volume, top gainers, most active, and market movers
- Stocktwits trending sectors, most active tickers, watcher growth, and
  bullish/bearish rankings
- Blossom creator-position observations when manually visible, grouped by
  sector or theme
- Alpaca/GDELT/company news acceleration
- Sector-specific catalyst themes already tracked in the research folder

## Dashboard Behavior

`watchlist-variable-mass-change` uses the same next-close execution convention
as other variable portfolios:

- observe signal information after one market close
- execute simulated entries/exits at the next available close
- deploy `$1,000` per entry
- use the mass-change CSV as its universe

An empty CSV intentionally produces an empty portfolio. Add candidates as they
are discovered and verified.

## Promotion Rules

Do not move a candidate from mass-change into another watchlist yet. The next
phase is to design explicit rules that allow stocks to move in and out of
portfolios automatically.

Future promotion candidates should require evidence beyond attention:

- fresh, strict, or near technical signal
- improving volume profile
- news or creator catalyst that predates the move
- acceptable price extension and risk

Mass-change is for sector-led discovery. The other watchlists are for stronger
conviction after explicit promotion rules exist.
