# Free Analyst Pick Portfolios

Research date: 2026-06-05

## Scope

These are not private analyst holdings or disclosed personal portfolios. They are equal-dollar paper portfolios built from visible public analyst-rating pages. Each included ticker is a visible Buy-rated stock from a high-ranked analyst page and is added to `PAPER_TRADING/data/trades.csv` as a $1,000 paper buy.

Hold-rated, Sell-rated, redacted, paywalled, or unverifiable rows were excluded. The purpose is to track whether publicly visible analyst pick baskets add useful signal compared with the existing trader, watchlist, and derived-strategy portfolios.

## Source Method

Primary source: StockAnalysis analyst rankings, which lists analyst success rate, average return, rating count, recency, and states that analyst data is sourced from TipRanks and recalculated daily.

Selected analyst pages:

- Nathan Jones, Stifel Nicolaus: high-ranked industrials analyst with visible Buy-rated industrial names.
- Patrick Brown, Raymond James: high-ranked freight, trucking, rail, and materials analyst with visible Buy-rated names.
- Chris Dendrinos, RBC Capital: high-ranked technology/clean-tech analyst with visible Buy-rated renewable and clean-tech names.
- Mike Mayo, Wells Fargo: high-ranked financials analyst with visible Buy-rated bank and capital markets names.

## Added Portfolios

### analyst-nathan-jones

Visible Buy-rated tickers added:

- `FLS`
- `IEX`
- `AOS`
- `HLIO`
- `THRM`
- `GTX`
- `CR`

Excluded visible rows:

- `CW`, `DCI`, `LNN`: Hold-rated.
- Redacted rows: hidden behind the free-page limit.

### analyst-patrick-brown

Visible Buy-rated tickers added:

- `XPO`
- `SAIA`
- `ODFL`
- `VMC`
- `MLM`
- `ROAD`
- `UNP`
- `CSX`
- `HUBG`

Excluded visible rows:

- `FDXF`: omitted because it appears to be a newer/special listing and should be verified before treating it as a normal dashboard-tradable ticker.
- Redacted rows: hidden behind the free-page limit.

### analyst-chris-dendrinos

Visible Buy-rated tickers added:

- `NXT`
- `RUN`
- `ORA`
- `HASI`

Excluded visible rows:

- `CHPT`, `WPRT`, `PLUG`, `SMR`, `FLNC`, `SEDG`: Hold-rated.
- Redacted rows: hidden behind the free-page limit.

### analyst-mike-mayo

Visible Buy-rated tickers added:

- `FITB`
- `BAC`
- `JPM`
- `STT`
- `C`
- `GS`

Excluded visible rows:

- `WBS`, `RF`: Sell-rated.
- `NTRS`, `MS`: Hold-rated.
- Redacted rows: hidden behind the free-page limit.

## Dashboard Interpretation

These portfolios should be read as analyst recommendation baskets, not conviction-weighted portfolios. Every included stock is assigned the standard $1,000 stock allocation so the dashboard can compare returns consistently with the other paper-ledger traders.

Useful comparisons:

- Compare each analyst basket against `watchlist-master` and the active signal portfolios from the same start/end dates.
- Review whether analyst-pick baskets add sector diversification or simply duplicate existing signal names.
- Watch concentration because these baskets are intentionally sector-specific.

## Links

- StockAnalysis top analyst rankings: https://stockanalysis.com/analysts/
- Nathan Jones: https://stockanalysis.com/analysts/nathan-jones/
- Patrick Brown: https://stockanalysis.com/analysts/patrick-brown/
- Chris Dendrinos: https://stockanalysis.com/analysts/chris-dendrinos/
- Mike Mayo: https://stockanalysis.com/analysts/mike-mayo/
